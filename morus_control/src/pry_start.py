def odometry_callback(self, data):
    """Callback function for odometry subscriber"""

    self.first_measurement = True

    self.x_mv = data.pose.pose.position.x
    self.y_mv = data.pose.pose.position.y
    self.z_mv = data.pose.pose.position.z

    self.vx_mv = data.twist.twist.linear.x
    self.vy_mv = data.twist.twist.linear.y
    self.vz_mv = data.twist.twist.linear.z

    self.p = data.twist.twist.angular.x
    self.q = data.twist.twist.angular.y
    self.r = data.twist.twist.angular.z

    self.qx = data.pose.pose.orientation.x
    self.qy = data.pose.pose.orientation.y
    self.qz = data.pose.pose.orientation.z
    self.qw = data.pose.pose.orientation.w


def get_pitch_roll_yaw(self, qx, qy, qz, qw):
    """Calculate roll, pitch and yaw angles/rates with quaternions"""

    # conversion quaternion to euler (yaw - pitch - roll)
    self.euler_mv.x = math.atan2(2 * (qw * qx + qy * qz), qw * qw
                                 - qx * qx - qy * qy + qz * qz)
    self.euler_mv.y = math.asin(2 * (qw * qy - qx * qz))
    self.euler_mv.z = math.atan2(2 * (qw * qz + qx * qy), qw * qw
                                 + qx * qx - qy * qy - qz * qz)

    # gyro measurements (p,q,r)
    p = self.p
    q = self.q
    r = self.r

    sx = math.sin(self.euler_mv.x)  # sin(roll)
    cx = math.cos(self.euler_mv.x)  # cos(roll)
    cy = math.cos(self.euler_mv.y)  # cos(pitch)
    ty = math.tan(self.euler_mv.y)  # cos(pitch)

    # conversion gyro measurements to roll_rate, pitch_rate, yaw_rate
    self.euler_rate_mv.x = p + sx * ty * q + cx * ty * r
    self.euler_rate_mv.y = cx * q - sx * r
    self.euler_rate_mv.z = sx / cy * q + cx / cy * r