"""
CARE-VLM Remote Wireless Camera Streaming
Phone camera streams to server over internet (no shared network needed)
Phone on 4G, Server anywhere - completely independent
"""

import cv2
import numpy as np
import threading
import socket
import json
from datetime import datetime
from collections import deque
import base64
import time

# ============================================================================
# OPTION 1: PHONE APP → RTMP/HTTP STREAM → SERVER
# (Phone broadcasts stream, server receives)
# ============================================================================

class RemoteStreamReceiver:
    """
    Receive video stream from phone over internet
    Phone uses apps like:
    - RTMP Publisher (broadcasts via RTMP)
    - Wowza GoCoder (RTMP streaming)
    - OBS Mobile (RTMP/HTTP)
    - GStreamer (HTTP/RTMP)
    """
    
    def __init__(self, stream_url: str, stream_type: str = "rtmp"):
        """
        Args:
            stream_url: Remote stream URL
            stream_type: "rtmp" (real-time), "http" (HTTP stream), "hls" (HTTP Live Stream)
        
        Example URLs:
            RTMP: rtmp://server.com:1935/live/camera1
            HTTP: http://phone-ip:8080/stream
            HLS: http://phone-ip:8080/stream.m3u8
        """
        self.stream_url = stream_url
        self.stream_type = stream_type
        self.cap = None
        self.is_connected = False
        self.setup_stream()
    
    def setup_stream(self):
        """Setup remote stream connection"""
        print(f"📡 Connecting to remote stream ({self.stream_type.upper()})")
        print(f"   URL: {self.stream_url}")
        
        # Set connection parameters based on type
        if self.stream_type.lower() == "rtmp":
            # RTMP stream
            print("   Protocol: RTMP (Real-Time Messaging Protocol)")
        elif self.stream_type.lower() == "http":
            # HTTP MJPEG stream
            print("   Protocol: HTTP MJPEG")
        elif self.stream_type.lower() == "hls":
            # HLS stream
            print("   Protocol: HLS (HTTP Live Stream)")
        
        self.cap = cv2.VideoCapture(self.stream_url)
        
        if not self.cap or not self.cap.isOpened():
            print(f"❌ Failed to connect to remote stream")
            print(f"   • Check URL is correct")
            print(f"   • Check phone app is broadcasting")
            print(f"   • Check firewall/router settings")
            raise Exception("Remote stream connection failed")
        
        self.is_connected = True
        print("✅ Connected to remote stream!")
    
    def read_frame(self):
        """Get frame from remote stream"""
        if not self.is_connected:
            return None
        
        ret, frame = self.cap.read()
        if not ret:
            print("⚠️  Lost connection to remote stream")
            self.is_connected = False
            return None
        
        return frame
    
    def reconnect(self):
        """Reconnect if connection lost"""
        print("🔄 Attempting to reconnect...")
        try:
            self.setup_stream()
            print("✅ Reconnected!")
            return True
        except:
            print("❌ Reconnection failed")
            return False


# ============================================================================
# OPTION 2: PHONE BROADCASTS FRAMES VIA HTTP POST
# (Phone sends frames to server)
# ============================================================================

class HTTPFrameServer:
    """
    HTTP server that receives frames from phone
    Phone sends frames via HTTP POST
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 5000):
        """
        Args:
            host: Server host (0.0.0.0 for all interfaces)
            port: Server port
        
        Usage:
            1. Start server: server = HTTPFrameServer()
            2. Phone sends: POST http://server-ip:5000/frame (with frame data)
            3. Server receives and processes
        """
        self.host = host
        self.port = port
        self.frame_buffer = deque(maxlen=1)  # Keep latest frame
        self.latest_frame = None
        self.latest_timestamp = None
        self.running = False
        
        print(f"📡 HTTP Frame Server ready at {host}:{port}")
        print(f"   Phone should POST to: http://{self._get_local_ip()}:{port}/frame")
    
    def _get_local_ip(self):
        """Get local IP address"""
        try:
            # Connect to external server to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "localhost"
    
    def start(self):
        """Start HTTP server"""
        try:
            from flask import Flask, request
        except ImportError:
            print("❌ Flask required: pip install flask")
            return
        
        app = Flask(__name__)
        
        @app.route('/frame', methods=['POST'])
        def receive_frame():
            """Receive frame from phone"""
            try:
                # Get frame data from request
                data = request.get_json()
                frame_b64 = data.get('frame')  # base64 encoded frame
                timestamp = data.get('timestamp')
                
                if not frame_b64:
                    return {'status': 'error', 'message': 'No frame data'}, 400
                
                # Decode base64 to numpy array
                frame_data = base64.b64decode(frame_b64)
                nparr = np.frombuffer(frame_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                # Store latest frame
                self.latest_frame = frame
                self.latest_timestamp = timestamp
                
                return {'status': 'success', 'message': 'Frame received'}, 200
            except Exception as e:
                return {'status': 'error', 'message': str(e)}, 500
        
        @app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            return {
                'status': 'ok',
                'latest_frame_time': self.latest_timestamp,
                'frames_received': len(self.frame_buffer)
            }, 200
        
        print(f"🚀 Starting HTTP server on {self.host}:{self.port}")
        self.running = True
        
        # Run in thread
        def run_server():
            app.run(host=self.host, port=self.port, debug=False)
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
    
    def get_frame(self):
        """Get latest received frame"""
        return self.latest_frame


# ============================================================================
# OPTION 3: PHONE STREAMS VIA WEBSOCKET
# (Bidirectional streaming + commands)
# ============================================================================

class WebSocketStreamReceiver:
    """
    WebSocket-based streaming from phone
    More efficient than HTTP, supports two-way communication
    """
    
    def __init__(self, ws_url: str):
        """
        Args:
            ws_url: WebSocket URL (e.g., ws://phone-ip:8080/stream)
        """
        self.ws_url = ws_url
        self.latest_frame = None
        self.running = False
        
        print(f"📡 WebSocket Stream Receiver")
        print(f"   URL: {ws_url}")
        print(f"   (Requires websocket-client library)")
    
    def start(self):
        """Start WebSocket connection"""
        try:
            import websocket
        except ImportError:
            print("❌ websocket-client required: pip install websocket-client")
            return
        
        print("🔄 Connecting to WebSocket stream...")
        
        def on_message(ws, message):
            """Receive message from WebSocket"""
            try:
                # Decode frame from message
                frame_data = base64.b64decode(message)
                nparr = np.frombuffer(frame_data, np.uint8)
                self.latest_frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            except Exception as e:
                print(f"Error decoding frame: {e}")
        
        def on_error(ws, error):
            print(f"❌ WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            print("⚠️  WebSocket closed")
            self.running = False
        
        def on_open(ws):
            print("✅ WebSocket connected!")
            self.running = True
        
        ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        # Run in thread
        ws_thread = threading.Thread(target=ws.run_forever, daemon=True)
        ws_thread.start()
    
    def get_frame(self):
        """Get latest frame"""
        return self.latest_frame


# ============================================================================
# OPTION 4: CLOUD STORAGE RELAY
# (Phone uploads to cloud, server downloads)
# ============================================================================

class CloudStorageRelay:
    """
    Phone uploads frames to cloud storage (S3, Google Cloud, etc.)
    Server downloads and processes
    Useful for async processing
    """
    
    def __init__(self, storage_type: str = "s3", bucket: str = "care-vlm"):
        """
        Args:
            storage_type: "s3", "gcs" (Google Cloud), "azure"
            bucket: Bucket/container name
        """
        self.storage_type = storage_type
        self.bucket = bucket
        
        print(f"☁️  Cloud Storage Relay")
        print(f"   Type: {storage_type.upper()}")
        print(f"   Bucket: {bucket}")
    
    def get_latest_frame(self):
        """Get latest frame from cloud storage"""
        if self.storage_type == "s3":
            # AWS S3
            try:
                import boto3
                s3 = boto3.client('s3')
                obj = s3.get_object(Bucket=self.bucket, Key='latest_frame.jpg')
                frame_data = obj['Body'].read()
                nparr = np.frombuffer(frame_data, np.uint8)
                return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            except ImportError:
                print("❌ boto3 required: pip install boto3")
                return None
        
        elif self.storage_type == "gcs":
            # Google Cloud Storage
            try:
                from google.cloud import storage
                client = storage.Client()
                bucket = client.bucket(self.bucket)
                blob = bucket.blob('latest_frame.jpg')
                frame_data = blob.download_as_bytes()
                nparr = np.frombuffer(frame_data, np.uint8)
                return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            except ImportError:
                print("❌ google-cloud-storage required")
                return None
        
        return None


# ============================================================================
# UNIFIED WIRELESS CAMERA HANDLER
# ============================================================================

class WirelessCameraCapture:
    """
    Unified handler for all wireless camera methods
    Auto-detects and connects to any wireless camera source
    """
    
    def __init__(self, method: str = "http", source: str = None):
        """
        Args:
            method: "rtmp" | "http" | "hls" | "http_post" | "websocket" | "cloud"
            source: URL or configuration
        
        Examples:
            # RTMP stream from phone
            WirelessCameraCapture(method="rtmp", source="rtmp://server:1935/live/camera")
            
            # HTTP stream from phone
            WirelessCameraCapture(method="http", source="http://phone-ip:8080/stream")
            
            # HTTP POST (server receives from phone)
            WirelessCameraCapture(method="http_post", source="localhost:5000")
        """
        self.method = method
        self.source = source
        self.camera = None
        self.setup_camera()
    
    def setup_camera(self):
        """Setup camera based on method"""
        print(f"\n📡 Wireless Camera Setup ({self.method.upper()})")
        print("="*60)
        
        if self.method == "rtmp":
            self.camera = RemoteStreamReceiver(self.source, "rtmp")
        
        elif self.method == "http":
            self.camera = RemoteStreamReceiver(self.source, "http")
        
        elif self.method == "hls":
            self.camera = RemoteStreamReceiver(self.source, "hls")
        
        elif self.method == "http_post":
            host, port = self.source.split(":") if ":" in self.source else ("0.0.0.0", "5000")
            self.camera = HTTPFrameServer(host=host, port=int(port))
            self.camera.start()
        
        elif self.method == "websocket":
            self.camera = WebSocketStreamReceiver(self.source)
            self.camera.start()
        
        elif self.method == "cloud":
            self.camera = CloudStorageRelay("s3", "care-vlm")
        
        print("="*60 + "\n")
    
    def read_frame(self):
        """Get next frame"""
        if hasattr(self.camera, 'read_frame'):
            return self.camera.read_frame()
        elif hasattr(self.camera, 'get_frame'):
            return self.camera.get_frame()
        return None
    
    def is_connected(self):
        """Check if camera is connected"""
        return getattr(self.camera, 'is_connected', True)


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    """
    EXAMPLE 1: RTMP Stream from Phone
    ──────────────────────────────────
    1. Phone broadcasts via RTMP (apps: Wowza GoCoder, OBS Mobile)
    2. Server receives stream
    
    Setup:
        camera = WirelessCameraCapture(
            method="rtmp",
            source="rtmp://server-ip:1935/live/camera1"
        )
    """
    
    """
    EXAMPLE 2: HTTP Stream from Phone
    ──────────────────────────────────
    1. Phone has IP camera app (IP Webcam, Codeshot)
    2. Phone broadcasts HTTP stream on port 8080
    3. Server connects and receives
    
    Setup:
        camera = WirelessCameraCapture(
            method="http",
            source="http://phone-ip:8080/video"
        )
    """
    
    """
    EXAMPLE 3: HTTP POST (Phone Uploads to Server)
    ───────────────────────────────────────────────
    1. Server starts HTTP listener on port 5000
    2. Phone sends frames via HTTP POST
    3. Server receives and processes
    
    Setup:
        camera = WirelessCameraCapture(
            method="http_post",
            source="0.0.0.0:5000"
        )
    """
    
    """
    EXAMPLE 4: WebSocket (Bidirectional)
    ────────────────────────────────────
    1. Phone connects via WebSocket
    2. Server sends commands, receives frames
    3. More efficient than HTTP
    
    Setup:
        camera = WirelessCameraCapture(
            method="websocket",
            source="ws://phone-ip:8080/stream"
        )
    """
    
    """
    EXAMPLE 5: Cloud Storage (Async Processing)
    ────────────────────────────────────────────
    1. Phone uploads to AWS S3 / Google Cloud
    2. Server downloads and processes
    3. Good for async, geo-distributed setup
    
    Setup:
        camera = WirelessCameraCapture(
            method="cloud",
            source="s3://care-vlm-bucket"
        )
    """
    
    # Recommended: HTTP Stream (most reliable)
    print("To test, use HTTP stream from phone:")
    print("1. Install IP camera app (IP Webcam)")
    print("2. Note the URL shown in app")
    print("3. Replace 'phone-ip' below:")
    
    # Example (uncomment to test):
    # camera = WirelessCameraCapture(
    #     method="http",
    #     source="http://192.168.1.100:8080/video"
    # )
    # 
    # while True:
    #     frame = camera.read_frame()
    #     if frame is not None:
    #         cv2.imshow("Remote Camera", frame)
    #         if cv2.waitKey(1) & 0xFF == ord('q'):
    #             break
