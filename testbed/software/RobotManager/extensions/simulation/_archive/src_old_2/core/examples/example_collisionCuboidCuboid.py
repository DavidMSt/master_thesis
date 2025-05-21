import math
from scioi_py_core.core.archive.collisionCuboidCuboid import Box
from scioi_py_core.utils.plot import CubePlotBox, plot_points, plot_3d_vectors
from matplotlib import pyplot as plt


class ExampleBoxes(Box):

    def __init__(self):
        # create two boxes
        self.box1 = Box(center=[6, 4, 1], size_x=3, size_y=2, size_z=1,
                        angles=(math.radians(20), math.radians(45), math.radians(0)))
        self.box2 = Box(center=[1, 1, 1], size_x=3, size_y=2, size_z=1, angles=(0, 0, 0))

        # origin for vector plotting
        self.origin = [0, 0, 0]
        self.test_points = [[1, 0, 0]]

    def example_plot_boxes(self):
        """
        create and plot two boxes
        :return: nothing
        """

        # plot both
        cpb1 = CubePlotBox(self.box1.width, self.box1.center, self.box1.get_R(), [0, 0, 1], ax)
        cpb2 = CubePlotBox(self.box1.width, self.box1.center, self.box1.get_R(), [0, 1, 0], ax)

    def example_plot_collision_points(self):
        """
        plot collision points of the two boxes
        :return: nothing
        """
        plot_points(self.box1.detect_collided_points(self.box2), ax)

    @staticmethod
    def example_plot_3d_vectors(vector, ax):
        """
        plot a 3d vector via matplotlib
        :param vector: vector that is going to be plotted
        :return: nothing
        """
        plot_3d_vectors(ax=ax)

    @staticmethod
    def example_calculate_angles(ax=None):
        """
        example for calculating angles for all 3 axes
        :return: nothing
        """
        example_vector = [1, 3, 3]
        angle_x = Box.get_angle(vector=example_vector, axis='xyz', debug='x', ax=ax)
        testbox = ExampleBoxes
        testbox.example_plot_3d_vectors(example_vector)
        testbox.example_plot_3d_vectors([0, 0, 1])
        print(angle_x)

    def example_get_min_max_angle(self, ax):
        """
        example for getting the maximum and minimum angle for each axis by putting in one or more vectors
        :return: nothing
        """
        vec_ex_1 = [-1, -1, -1]
        vec_ex_2 = [-2, -1, -1]

        self.box1.get_min_max_angle([vec_ex_1, vec_ex_2], debug='y', ax=ax)


if __name__ == '__main__':
    plt.figure()
    plt.subplot(111, projection='3d')
    ax = plt.gca()
    ax.set_box_aspect([1, 1, 1])
    limitations = [-2, 2]
    ax.set_xlim([limitations[0], limitations[1]])
    ax.set_ylim([limitations[0], limitations[1]])
    ax.set_zlim([limitations[0], limitations[1]])

    ax.set_xlabel('x')
    ax.set_ylabel('y')
    ax.set_zlabel('z')

    # -------------------------------------------------------examples---------------------------------------------------
    example_box = ExampleBoxes()
    # ExampleBoxes.example_calculate_angles()
    example_box.example_get_min_max_angle(ax)

    # ------------------------------------------------------------------------------------------------------------------

    plt.show()
