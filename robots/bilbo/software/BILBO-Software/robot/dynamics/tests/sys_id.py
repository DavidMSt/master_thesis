import numpy as np


def estimate_system_and_lifted_matrix(u_list, y_list, L):
    """
    Estimate the impulse response h (of length L) for a SISO dynamic system
    from multiple input/output trajectory pairs and then compute the lifted
    system matrix P (a lower-triangular Toeplitz matrix).

    Parameters:
      u_list: list of numpy arrays
          Each array contains the input (torque) trajectory for one experiment.
      y_list: list of numpy arrays
          Each array contains the output (angle) trajectory corresponding to the input.
          It is assumed that len(u) == len(y) for each pair.
      L: int
          The number of impulse response coefficients to estimate. This also sets the
          dimensions of the lifted matrix P (L x L).

    Returns:
      h: numpy array of shape (L,)
          The estimated impulse response.
      P: numpy array of shape (L, L)
          The lifted system matrix where:
              P[i, j] = h[i - j] for i >= j, and 0 otherwise.
    """
    # Build a big regression problem from all trajectories.
    U_big = []
    Y_big = []

    for u, y in zip(u_list, y_list):
        T = len(u)
        # For each time step t in this trajectory,
        # form a row [u[t], u[t-1], ..., u[t-L+1]]
        for t in range(T):
            # Use 0 for indices t-k < 0 (causality)
            row = [u[t - k] if t - k >= 0 else 0 for k in range(L)]
            U_big.append(row)
            Y_big.append(y[t])

    U_big = np.array(U_big)
    Y_big = np.array(Y_big)

    # Solve the linear least squares problem U_big * h = Y_big
    h, residuals, rank, s = np.linalg.lstsq(U_big, Y_big, rcond=None)

    # Build the lifted system matrix P (L x L lower-triangular Toeplitz matrix)
    P = np.zeros((L, L))
    for i in range(L):
        for j in range(i + 1):  # Only fill entries for which i >= j.
            P[i, j] = h[i - j]

    return h, P


import numpy as np
import matplotlib.pyplot as plt


def system_identification(u_list, y_list, max_L=50, threshold=1e-3):
    """
    Estimate a discrete-time transfer function for a SISO system using multiple input/output trajectories.

    This function estimates an FIR model with a maximum impulse response length (max_L) and then
    determines the effective length (L_eff) by discarding coefficients that are small relative
    to the maximum coefficient (using the specified threshold).

    Parameters:
      u_list: list of numpy arrays
          Each array is an input trajectory.
      y_list: list of numpy arrays
          Each array is the corresponding output trajectory.
      max_L: int, optional
          The maximum number of impulse response coefficients to estimate (default: 50).
      threshold: float, optional
          Relative threshold to determine the effective impulse response length.
          Coefficients with absolute value below (threshold * max(|h|)) are considered negligible (default: 1e-3).

    Returns:
      tf: tuple (num, den)
          The estimated discrete-time transfer function where 'num' is a numpy array of the impulse
          response coefficients (truncated to the effective length) and 'den' is np.array([1.0]).
      L_eff: int
          The effective impulse response length.
    """
    # Build the regression problem by stacking all the data.
    U_big = []
    Y_big = []
    for u, y in zip(u_list, y_list):
        T = len(u)
        for t in range(T):
            # Create row: [u[t], u[t-1], ..., u[t-max_L+1]] (using 0 for negative indices)
            row = [u[t - k] if t - k >= 0 else 0 for k in range(max_L)]
            U_big.append(row)
            Y_big.append(y[t])

    U_big = np.array(U_big)
    Y_big = np.array(Y_big)

    # Solve the least squares problem U_big * h = Y_big to get a full impulse response estimate.
    h_full, residuals, rank, s = np.linalg.lstsq(U_big, Y_big, rcond=None)

    # Determine the effective impulse response length L_eff:
    h_abs = np.abs(h_full)
    max_val = np.max(h_abs)
    above_thresh = np.where(h_abs >= threshold * max_val)[0]
    if above_thresh.size == 0:
        L_eff = 1  # At least one coefficient is kept
    else:
        L_eff = above_thresh[-1] + 1  # +1 since indices start at 0

    # Truncate the impulse response to the effective length.
    h_eff = h_full[:L_eff]

    # FIR model transfer function: G(z) = num(z)/den(z) with den(z) = 1.
    tf = (h_eff, np.array([1.0]))

    return tf, L_eff


def compute_P_from_tf(tf, P_size):
    """
    Compute the lifted system matrix P from a given transfer function (FIR model)
    with a specified matrix size.

    Parameters:
      tf: tuple (num, den)
          The discrete-time transfer function, where 'num' is a numpy array of impulse
          response coefficients and 'den' is a numpy array (typically [1] for FIR models).
      P_size: int
          The desired size (number of rows/columns) of the square P matrix.

    Returns:
      P: numpy array of shape (P_size, P_size)
          The lifted system matrix, where for indices i >= j:
              P[i, j] = h[i - j] if (i - j) is within the impulse response length,
                        0 otherwise.
    """
    num, den = tf  # For an FIR model, den should be [1.0] and num is the impulse response.
    h = num
    L = len(h)

    P = np.zeros((P_size, P_size))
    for i in range(P_size):
        for j in range(i + 1):
            k = i - j  # Index difference, corresponds to the impulse response delay.
            if k < L:
                P[i, j] = h[k]
            # else: remains 0
    return P


# Example usage and test plot:
if __name__ == "__main__":
    # Generate synthetic data for demonstration:
    # True impulse response (FIR of length 4)
    h_true = np.array([0.5, 0.3, 0.1, 0.05])
    L_true = len(h_true)

    # Create multiple experiments (trajectories), each of length T.
    N = 5  # number of experiments
    T = 50  # length of each trajectory
    u_list = []
    y_list = []
    np.random.seed(5)
    for _ in range(N):
        u = np.random.randn(T)
        y = np.zeros(T)
        for t in range(T):
            # Convolve with the true impulse response (causal convolution)
            for k in range(L_true):
                if t - k >= 0:
                    y[t] += h_true[k] * u[t - k]
        # Optionally add some noise:
        y += 0.05 * np.random.randn(T)
        u_list.append(u)
        y_list.append(y)

    # Estimate the transfer function using all experiments.
    tf, L_eff = system_identification(u_list, y_list, max_L=20, threshold=1e-3)
    num, den = tf
    print("Estimated Transfer Function:")
    print("Numerator coefficients (impulse response):", num)
    print("Denominator coefficients:", den)
    print("Effective impulse response length L_eff:", L_eff)

    P = compute_P_from_tf(tf, 50)
    # Select one experiment (e.g., the first) for testing.
    u_test = u_list[1]
    y_actual = y_list[1]

    # Estimate the output by convolving the input with the estimated impulse response.
    # Note: We take the first T samples from the full convolution result.
    # y_est = np.convolve(u_test, num)[:T]
    y_est = P @ np.asarray(u_test)

    # Plot the actual and estimated output.
    plt.figure(figsize=(10, 5))
    plt.plot(y_actual, label="Actual Output")
    plt.plot(y_est, label="Estimated Output", linestyle='--')
    plt.xlabel("Time Step")
    plt.ylabel("Output")
    plt.title("Actual vs Estimated Output")
    plt.legend()
    plt.grid(True)
    plt.show()


#
# # Example usage:
# if __name__ == "__main__":
#     # Generate synthetic data for demonstration:
#     # True impulse response (FIR of length 4)
#     h_true = np.array([0.5, 0.3, 0.1, 0.05])
#     L = len(h_true)
#
#     # Create N experiments (trajectories) each of length T
#     N = 5
#     T = 50
#     u_list = []
#     y_list = []
#     np.random.seed(0)
#     for _ in range(N):
#         u = np.random.randn(T)
#         y = np.zeros(T)
#         for t in range(T):
#             # Convolve with the true impulse response (with causality)
#             for k in range(L):
#                 if t - k >= 0:
#                     y[t] += h_true[k] * u[t - k]
#         # Optionally add some noise:
#         y += 0.01 * np.random.randn(T)
#         u_list.append(u)
#         y_list.append(y)
#
#     # Estimate impulse response and lifted matrix
#     h_est, P_est = estimate_system_and_lifted_matrix(u_list, y_list, L)
#
#     print("Estimated impulse response h:")
#     print(h_est)
#     print("\nLifted system matrix P:")
#     print(P_est)
