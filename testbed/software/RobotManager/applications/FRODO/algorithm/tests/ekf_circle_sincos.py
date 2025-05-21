import numpy as np
import math
import qmt


def R(angle):
    """2D rotation matrix for a given angle (in radians)."""
    return np.array([
        [math.cos(angle), -math.sin(angle)],
        [math.sin(angle), math.cos(angle)]
    ])


# --- State Representation ---
# For each agent the state is [x, y, sin(psi), cos(psi)].
# We define our full state X as:
#   Agent 1 (anchor): indices 0-3
#   Agent 2 (relative): indices 4-7
#   Agent 3 (relative): indices 8-11

def h_12(X):
    """
    Measurement from Agent 1 observing Agent 2.
    Since Agent 1 is the anchor, its measurement is directly the relative state of Agent 2:
      [r21_x, r21_y, sin(r21_psi), cos(r21_psi)]
    """
    return X[4:8]


def h_23(X):
    """
    Measurement from Agent 2 observing Agent 3.

    The predicted measurement is computed as follows:
      - Extract Agent 2's relative state: position (r21_x, r21_y) and orientation [sin, cos].
      - Compute psi2 = atan2(sin(r21_psi), cos(r21_psi)).
      - Similarly, extract Agent 3's state and compute psi3.
      - Transform the difference in positions into Agent 2's frame:
            trans = R(-psi2) @ ( [r31_x, r31_y] - [r21_x, r21_y] )
      - The relative orientation difference is dpsi = psi3 - psi2.
      - Represent the orientation difference as [sin(dpsi), cos(dpsi)].
    """
    # Agent 2 state (indices 4:8)
    r21 = X[4:8]
    r21_pos = r21[0:2]
    r21_sin = r21[2]
    r21_cos = r21[3]
    psi2 = math.atan2(r21_sin, r21_cos)

    # Agent 3 state (indices 8:12)
    r31 = X[8:12]
    r31_pos = r31[0:2]
    r31_sin = r31[2]
    r31_cos = r31[3]
    psi3 = math.atan2(r31_sin, r31_cos)

    delta = r31_pos - r21_pos
    trans = R(-psi2) @ delta
    dpsi = psi3 - psi2
    return np.hstack((trans, math.sin(dpsi), math.cos(dpsi)))


def h_31(X):
    """
    Measurement from Agent 3 observing Agent 1.

    Agent 3’s state is given by [r31_x, r31_y, sin(r31_psi), cos(r31_psi)].
    The inverse (i.e. how Agent 1 appears from Agent 3) is computed as:
      - t_inv = -R(-psi3) @ [r31_x, r31_y]
      - The orientation part is represented by [sin(-psi3), cos(-psi3)]
        which simplifies to [-sin(psi3), cos(psi3)].
    """
    r31 = X[8:12]
    r31_pos = r31[0:2]
    r31_sin = r31[2]
    r31_cos = r31[3]
    psi3 = math.atan2(r31_sin, r31_cos)

    t_inv = - R(-psi3) @ r31_pos
    return np.hstack((t_inv, -math.sin(psi3), math.cos(psi3)))


def h_all(X):
    """
    Stacked measurement function.
    Returns a 12-dimensional vector:
      [h_12(X); h_23(X); h_31(X)]
    """
    return np.hstack((h_12(X), h_23(X), h_31(X)))


def finite_difference_jacobian(func, X, epsilon=1e-6):
    """
    Computes the Jacobian of a function 'func' at X using finite differences.
    """
    n = len(X)
    m = len(func(X))
    J = np.zeros((m, n))
    for i in range(n):
        dX = np.zeros(n)
        dX[i] = epsilon
        J[:, i] = (func(X + dX) - func(X - dX)) / (2 * epsilon)
    return J


def ekf_update(X, P, z, R_meas, h_func):
    """
    Standard EKF update step.

    Note: Since our measurement functions now output continuous sin/cos values,
    no wrapping is necessary.
    """
    z_pred = h_func(X)
    y = z - z_pred
    H = finite_difference_jacobian(h_func, X)
    S = H @ P @ H.T + R_meas
    K = P @ H.T @ np.linalg.inv(S)
    X_new = X + K @ y
    P_new = (np.eye(len(X)) - K @ H) @ P
    return X_new, P_new


def main():
    # --- True States ---
    # Agent 1 (anchor): x, y, sin(psi), cos(psi) with psi = 0.
    x1_true = np.array([0.0, 0.0, math.sin(0.0), math.cos(0.0)])

    # Agent 2 absolute state:
    psi2 = math.radians(90)  # 135° in radians
    x2_true = np.array([1, 1, math.sin(psi2), math.cos(psi2)])

    # Agent 3 absolute state:
    psi3 = math.radians(-90)  # -90° in radians
    x3_true = np.array([0.0, 1.0, math.sin(psi3), math.cos(psi3)])

    # --- Relative States ---
    # Compute the relative state of Agent 2 with respect to Agent 1.
    # For the translation part, we have: r21 = x2 - x1.
    # For the orientation, since psi1=0, we have r21_psi = psi2.
    r21_true_pos = x2_true[0:2] - x1_true[0:2]
    r21_true = np.hstack((r21_true_pos, math.sin(psi2), math.cos(psi2)))

    # Similarly, for Agent 3:
    r31_true_pos = x3_true[0:2] - x1_true[0:2]
    r31_true = np.hstack((r31_true_pos, math.sin(psi3), math.cos(psi3)))

    # Full true state vector:
    # [Agent1; Agent2 relative; Agent3 relative]
    X_true = np.hstack((x1_true, r21_true, r31_true))

    # --- Initial Estimate ---
    # Agent 1 is known perfectly.
    x1_est = x1_true.copy()
    # For Agents 2 and 3, we start with zero translation and an orientation corresponding to 0 (i.e., sin(0)=0, cos(0)=1).
    r21_est = np.array([0.0, 0.0, 0.0, 1.0])
    r31_est = np.array([0.0, 0.0, 0.0, 1.0])
    X_est = np.hstack((x1_est, r21_est, r31_est))

    # --- Covariance ---
    # Use small covariance for Agent 1 and larger covariance for the relative states.
    P1 = np.diag([1e-6, 1e-6, 1e-6, 1e-6])
    P2 = np.diag([1.0, 1.0, 0.1, 0.1])
    P3 = np.diag([1.0, 1.0, 0.1, 0.1])
    P_est = np.block([
        [P1, np.zeros((4, 4)), np.zeros((4, 4))],
        [np.zeros((4, 4)), P2, np.zeros((4, 4))],
        [np.zeros((4, 4)), np.zeros((4, 4)), P3]
    ])

    # --- Measurement Noise ---
    # Now each measurement is 4-dimensional.
    sigma12 = np.array([1e-4, 1e-4, 1e-4, 1e-4])
    sigma23 = np.array([1e-4, 1e-4, 1e-4, 1e-4])
    sigma31 = np.array([1e-4, 1e-4, 1e-4, 1e-4])
    R12 = np.diag(sigma12 ** 2)
    R23 = np.diag(sigma23 ** 2)
    R31 = np.diag(sigma31 ** 2)
    R_meas = np.block([
        [R12, np.zeros((4, 4)), np.zeros((4, 4))],
        [np.zeros((4, 4)), R23, np.zeros((4, 4))],
        [np.zeros((4, 4)), np.zeros((4, 4)), R31]
    ])

    num_steps = 100
    print("Step | Estimated State and Frobenius Norm of Covariance")
    for step in range(num_steps):
        # Simulate measurements based on the true state.
        z_true = h_all(X_true)
        noise = np.hstack((
            np.random.randn(4) * sigma12,
            np.random.randn(4) * sigma23,
            np.random.randn(4) * sigma31
        ))
        z_meas = z_true + noise

        # EKF update.
        X_est, P_est = ekf_update(X_est, P_est, z_meas, R_meas, h_all)

        frob_norm = np.linalg.norm(P_est, 'fro')
        s = ("Step {:2d}:\n"
             "  Agent1 (anchor): x={:6.3f}, y={:6.3f}, sin(psi)={:6.3f}, cos(psi)={:6.3f}\n"
             "  r21 (Agent2 relative): x={:6.3f}, y={:6.3f}, sin(psi)={:6.3f}, cos(psi)={:6.3f}\n"
             "  r31 (Agent3 relative): x={:6.3f}, y={:6.3f}, sin(psi)={:6.3f}, cos(psi)={:6.3f}\n"
             "  Frobenius norm of Covariance: {:8.4f}\n").format(
            step + 1,
            X_est[0], X_est[1], X_est[2], X_est[3],
            X_est[4], X_est[5], X_est[6], X_est[7],
            X_est[8], X_est[9], X_est[10], X_est[11],
            frob_norm)
        print(s)


if __name__ == "__main__":
    np.random.seed(42)
    main()
