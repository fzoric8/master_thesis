import rospy
import numpy as np
from std_msgs.msg import *



class TiltRotor:
    def __init__(self):

        self.ros_rate = rospy.Rate(10)
        self.pub_pitch_tilt0 = rospy.Publisher('/morus/angle_tilt_1_controller/command', Float64, queue_size=1)
        self.pub_pitch_tilt1 = rospy.Publisher('/morus/angle_tilt_3_controller/command', Float64, queue_size=1)
        self.pub_roll_tilt0 = rospy.Publisher('/morus/angle_tilt_0_controller/command', Float64, queue_size=1)
        self.pub_roll_tilt1 = rospy.Publisher('/morus/angle_tilt_2_controller/command', Float64, queue_size=1)
        self.tilt_angle = 0.0	


    def run(self):

        while not  rospy.is_shutdown():
            self.ros_rate.sleep()
            self.pub_pitch_tilt0.publish(self.tilt_angle)
            self.pub_pitch_tilt1.publish(-self.tilt_angle)
            self.pub_roll_tilt0.publish(self.tilt_angle)
            self.pub_roll_tilt1.publish(-self.tilt_angle)

if __name__=="__main__":
    rospy.init_node('angle_tilt')
    tilt_rotor = TiltRotor()
    tilt_rotor.run()
