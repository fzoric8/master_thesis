#!/usr/bin/python
# -*- coding: utf-8 -*-

import rospy
import numpy
import math
from geometry_msgs.msg import Vector3, PoseWithCovarianceStamped, PoseStamped, TwistStamped
from morus_msgs.msg import PIDController
from std_msgs.msg import *
from mav_msgs.msg import Actuators
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu
from pid import PID

VERBOSE = True



class AngleTiltCtl:

    def __init__(self):


        self.first_measurement = False
        self.t = 0
        self.t_old = 0

        # Initialize subscribers
        # Pose subscriber
        self.pose_sub = rospy.Subscriber(
            '/morus/pose',
            PoseStamped,
            self.pose_cb)
        # Odometry subscriber
        self.odometry = rospy.Subscriber(
            '/morus/odometry',
            Odometry,
            self.odometry_cb)
        # IMU subscriber
        self.imu = rospy.Subscriber(
            '/morus/Imu',
            Imu,
            self.imu_cb)
        # Pose reference subscriber
        self.pose_sp = rospy.Subscriber('/morus/pose_ref', Vector3, self.pose_sp_cb)
        self.angle_sp = rospy.Subscriber('/morus/angle_ref', Vector3, self.angle_sp_cb)

        # Initialize publishers, motor speed and tilt for roll and pitch
        self.pub_mot = rospy.Publisher('/gazebo/command/motor_speed', Actuators, queue_size=1)
        self.pub_roll_tilt0 = rospy.Publisher('/morus/angle_tilt_0_controller/command', Float64, queue_size=1)
        self.pub_roll_tilt1 = rospy.Publisher('/morus/angle_tilt_2_controller/command', Float64, queue_size=1)
        self.pub_pitch_tilt0 = rospy.Publisher('/morus/angle_tilt_1_controller/command', Float64, queue_size=1)
        self.pub_pitch_tilt1 = rospy.Publisher('/morus_angle_tilti_3_controller/command', Float64, queue_size=1)

        # Publishing PIDs in order to use dynamic reconfigure
        self.pub_PID_z = rospy.Publisher('PID_z', PIDController, queue_size=1)
        self.pub_PID_vz = rospy.Publisher('PID_vz', PIDController, queue_size=1)
        self.pub_pitch_rate_PID = rospy.Publisher('PID_pitch_rate', PIDController, queue_size=1)
        self.pub_pitch_PID = rospy.Publisher('PID_pitch', PIDController, queue_size=1)
        self.pub_roll_rate_PID = rospy.Publisher('PID_roll_rate', PIDController, queue_size=1)
        self.pub_roll_PID = rospy.Publisher('PID_roll', PIDController, queue_size=1)
        self.pub_yaw_PID = rospy.Publisher('PID_yaw_rate_PID', PIDController, queue_size=1)
        self.pub_angles = rospy.Publisher('rpy_angles', Vector3, queue_size=1)
        self.pub_angles_sp = rospy.Publisher('rpy_angles_sp', Vector3, queue_size=1)
        self.ros_rate = rospy.Rate(50)

        self.z_sp = 0                           # z-position set point
        self.z_ref_filt = 0                     # z ref filtered
        self.z_mv = 0                           # z-position measured value
        self.pid_z = PID()                      # pid instance for z control

        self.vz_sp = 0                          # vz velocity set_point
        self.vz_mv = 0                          # vz velocity measured value
        self.pid_vz = PID()                     # pid instance for z-velocity control

        self.euler_mv = Vector3(0., 0., 0)      # measured euler angles
        self.euler_sp = Vector3(0., 0., 0.)     # euler angles referent values
        self.pose_sp = Vector3(0., 0., 0.0)
        self.pose_mv = Vector3(0., 0., 0.)
        self.euler_rate_mv = Vector3(0, 0, 0)   # measured angular velocities
        self.roll_sp_filt, self.pitch_sp_filt, self.yaw_sp_filt = 0, 0, 0
        self.dwz = 0

        ########################################
        # Position control PIDs
        self.pid_x = PID(4, 1, 2, 0.05, -0.05)
        self.pid_y = PID(4, 1, 2, 0.05, -0.05)

        # Define PID for height control
        self.z_ref_filt = 0
        self.z_mv = 0

        self.pid_z = PID(4.1, 0.01, 1.5, 4, -4)
        self.pid_vz = PID(85, 0.1, 15, 200, -200)

        ########################################
        ########################################

        # initialize pitch_rate PID controller
        self.pitch_rate_PID = PID(2, 0.05, 1, 50, -50)
        self.pitch_PID = PID(75, 0, 1, 150, -150)

        # initialize roll rate PID controller
        self.roll_rate_PID = PID(2, 0.05, 1, 0.5, -0.5)
        self.roll_PID = PID(75, 0, 5, +150, -150)

        # initialize yaw rate PID controller
        self.yaw_rate_PID = PID(35, 2, 35, 50, -50)
        self.yaw_PID = PID(2, 0, 2, 30, -30)

    def pose_cb(self, msg):
        """
        Callback functon for assigning values from pose IMU

        :param msg: /morus/pose PoseStamped msg type used to extract pose and orientation of UAV

        """
        # entered subscribed callback func, set first_measurement flag as True
        self.first_measurement = True

        self.pose_mv.x = msg.pose.position.x
        self.pose_mv.y = msg.pose.position.y
        self.pose_mv.z = msg.pose.position.z

        self.qx = msg.pose.orientation.x
        self.qy = msg.pose.orientation.y
        self.qz = msg.pose.orientation.z
        self.qw = msg.pose.orientation.w


    def odometry_cb(self, msg):
        """
        Callback function for assigning values from odometry measurements

        :param msg: nav_msgs/Odometry,
        an estimate of position and velocity in free space
        """

        self.lin_x = msg.twist.twist.linear.x
        self.lin_y = msg.twist.twist.linear.y
        self.lin_z = msg.twist.twist.linear.z
        # TO DO: transform speeds global speed

        self.euler_rate_mv.x = msg.twist.twist.angular.x
        self.euler_rate_mv.y = msg.twist.twist.angular.y
        self.euler_rate_mv.z = msg.twist.twist.angular.z

    def pose_sp_cb(self, msg):

        self.pose_sp.x = msg.x
        self.pose_sp.y = msg.y
        self.pose_sp.z = msg.z

    def angle_sp_cb(self, msg):

        self.euler_sp.x = msg.x
        self.euler_sp.y = msg.y
        self.euler_sp.z = msg.z

    def imu_cb(self, msg):
        """
        Callback function used to extract measured values from IMU, lin_acc and ang_vel
        :param msg:
        :return:
        """

        self.lin_acc_x = msg.linear_acceleration.x
        ## TO DO: add rest if needed

    def quat_to_eul_conv(self, qx, qy, qz, qw):
        """
        Convert quaternions to euler angles (roll, pitch, yaw)
        """

        # roll (x-axis rotation)
        sinr = 2. * (qw * qx +  qy * qz)
        cosr = 1. - 2. * (qx * qx + qy * qy)
        self.roll = math.atan2(sinr, cosr)

        # pitch (y-axis rotation)
        sinp = 2. * (qw * qy - qz * qx)
        sinp = 1. if sinp > 1. else sinp
        sinp = -1. if sinp < -1. else sinp
        self.pitch = math.asin(sinp)

        # yaw (z-axis rotation)
        siny = 2. * (qw * qz + qx * qy)
        cosy = 1 - 2. * (qy * qy + qz * qz)
        self.yaw = math.atan2(siny, cosy)

        self.euler_mv.x = self.roll
        self.euler_mv.y = self.pitch
        self.euler_mv.z = self.yaw

    def run(self):
        """
        Runs quadcopter control algorithm
        """

        while not self.first_measurement:
            print("Waiting for first measurement")
            rospy.sleep(0.5)
        print("Started angle control")
        self.t_old = rospy.Time.now()

        while not rospy.is_shutdown():
            self.ros_rate.sleep()

            # discretization time
            t = rospy.Time.now()
            dt = (t - self.t_old).to_sec()
            if dt > 0.105 or dt < 0.095:
                print(dt)

            self.t_old = t
            self.quat_to_eul_conv(self.qx, self.qy, self.qz, self.qw)

            self.hover_speed = math.sqrt(293/0.000456874/4)

            # HEIGHT CONTROL:
            a = 0.2
            self.z_ref_filt = (1 - a) * self.z_ref_filt + a * self.pose_sp.z
            vz_ref = self.pid_z.compute(self.z_ref_filt, self.pose_mv.z, dt)
            domega_z = self.pid_vz.compute(vz_ref, self.vz_mv, dt)

            ## ATTITUDE CONTROL:

            # roll cascade (first PID -> roll ref, second PID -> roll_rate ref)
            #self.euler_sp.x = -self.pid_y.compute(self.pose_sp.y, self.pose_mv.y, dt)
            b = 0.5
            self.roll_sp_filt = (1 - b) * self.euler_sp.x + b * self.roll_sp_filt
            roll_rate_ref = self.roll_rate_PID.compute(self.roll_sp_filt, self.euler_mv.x, dt)
            dwx = self.roll_PID.compute(roll_rate_ref, self.euler_rate_mv.x, dt)

            # pitch cascade(first PID -> pitch ref, second PID -> pitch_rate ref)
            #self.euler_sp.y = self.pid_x.compute(self.pose_sp.x, self.pose_mv.x, dt)
            b = 0.5
            self.pitch_sp_filt = (1 - b) * self.euler_sp.y + b * self.pitch_sp_filt
            pitch_rate_ref = self.pitch_rate_PID.compute(self.pitch_sp_filt, self.euler_mv.y, dt)
            dwy = self.pitch_PID.compute(pitch_rate_ref, self.euler_rate_mv.y, dt)

            # yaw cascade (first PID -> yaw ref, second PID -> yaw_rate ref)
            a = 0.3
            self.yaw_sp_filt = (1 - a) * self.euler_sp.z + a * self.yaw_sp_filt
            yaw_rate_ref = self.yaw_rate_PID.compute(self.yaw_sp_filt, self.euler_mv.z, dt)
            dwz = self.yaw_PID.compute(yaw_rate_ref, self.euler_rate_mv.z, dt)


            if VERBOSE:

                print("Pitch speed: {}\n Roll speed: {}\n, Yaw speed: {}\n".format(dwy, dwx, dwz))
                print("Yaw measured_value:{}\n Yaw_reference_value:{}\n".format(self.euler_mv.z, self.euler_sp.z))
                print("Roll measured_value:{}\n, Roll_reference_value:{}\n".format(self.euler_mv.x, self.euler_sp.x))
                print("Pitch measured_value:{}\n, Pitch_reference_value:{}\n".format(self.euler_mv.y, self.euler_sp.y))
                print("x_m:{}\nx:{}\ny_m:{}\ny:{}\nz_m:{}\nz:{}".format(self.pose_mv.x, self.pose_sp.x,
                                                                        self.pose_mv.y, self.pose_sp.y,
                                                                        self.pose_mv.z,  self.pose_sp.z))



            samples_0 = numpy.random.normal(self.hoover_speed, 5, size=50000)
            samples_1 = numpy.random.normal(self.hoover_speed, 5, size=50000)
            samples_2 = numpy.random.normal(self.hoover_speed, 5, size=50000)
            samples_3 = numpy.random.normal(self.hoover_speed, 5, size=50000)



            #motor_speed_1 = self.hover_speed + domega_z + dwz - dwy
            #motor_speed_2 = self.hover_speed + domega_z - dwz #+ dwx
            #motor_speed_3 = self.hover_speed + domega_z + dwz + dwy
            #motor_speed_4 = self.hover_speed + domega_z - dwz #- dwx
            print(motor_speed_1, motor_speed_2, motor_speed_3, motor_speed_4)
            #print(self.z_sp, self.z_mv)

            if abs(roll_rate_ref - self.euler_rate_mv.x) < 10e-3:
                dwx = 0

            self.pub_roll_tilt0.publish(dwx)
            self.pub_roll_tilt1.publish(-dwx)

            # publish motor speeds
            motor_speed_msg = Actuators()
            motor_speed_msg.angular_velocities = [motor_speed_1, motor_speed_2,
                                                  motor_speed_3, motor_speed_4]

            # publish PID data -> could be useful for tuning
            self.pub_PID_z.publish(self.pid_z.create_msg())
            self.pub_PID_vz.publish(self.pid_vz.create_msg())
            self.pub_pitch_PID.publish(self.pitch_PID.create_msg())
            self.pub_pitch_rate_PID.publish(self.pitch_rate_PID.create_msg())
            self.pub_roll_PID.publish(self.roll_PID.create_msg())
            self.pub_roll_rate_PID.publish(self.roll_rate_PID.create_msg())
            self.pub_yaw_PID.publish(self.yaw_PID.create_msg())

            # publish_angles
            self.pub_angles.publish(self.euler_mv)
            self.pub_angles_sp.publish(self.euler_sp)

            self.pub_mot.publish(motor_speed_msg)



if __name__ == "__main__":
    rospy.init_node('morus_angle_tilt_ctl')
    angle_ctl = AngleTiltCtl()
    angle_ctl.run()
