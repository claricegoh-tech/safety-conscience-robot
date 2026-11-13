import threading
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import nclib

class RobotApiBridge(Node):
    def __init__(self):
        super().__init__('robot_api_bridge')
        
        # 1. PUBLISHER
        self.status_pub = self.create_publisher(
            String,
            '/robot_status',
            10
        )
        
        # 2. SUBSCRIBER
        self.status_sub = self.create_subscription(
            String,
            '/robot_info',
            self.status_callback,
            10
        )
        
        self.get_logger().info('Live Robot API Bridge initialized and listening.')

    def status_callback(self, msg):
        self.latest_robot_info = msg.data
        self.get_logger().info(f'Live update captured: "{self.latest_robot_info}"')
        
        if self.latest_robot_info == "robot info":
            # Spawn a daemon thread so the callback returns immediately without blocking ROS 2
            threading.Thread(target=self.tcp_request_worker, daemon=True).start()

    def tcp_request_worker(self):
        """Runs the blocking netcat operation safely in the background."""
        try:
            with nclib.Netcat(('192.168.10.10', 31001), timeout=2.0) as nc:
                nc.write(b"robot info\n")
                response_bytes = nc.read_timeout(1.0)
                
                if response_bytes:
                    robot_info_data = response_bytes.decode('utf-8', errors='ignore').strip()
                else:
                    robot_info_data = "Error: Robot TCP server returned no data (timeout)"

            # Publish result back to ROS 2 safely from the thread
            response_info = String()
            response_info.data = robot_info_data
            self.status_pub.publish(response_info)
            self.get_logger().info(f"TCP data published: {robot_info_data}")
            
        except Exception as e:
            self.get_logger().error(f"nclib connection failed: {str(e)}")
            error_msg = String(data="Error: netcat server unreachable")
            self.status_pub.publish(error_msg)

def main(args=None):
    rclpy.init(args=args)
    node = RobotApiBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()