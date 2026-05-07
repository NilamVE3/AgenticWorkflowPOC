# 🚀 Integration Platform Startup Guide

## **Method 1: Start Both Servers (Recommended)**

### **Terminal 1 - Start API Server**
```bash
cd integration_platform
python start_api.py
```

### **Terminal 2 - Start UI Server** 
```bash
cd integration_platform
python start_ui.py
```

## **Method 2: Quick Start**

### **Start API Server Only**
```bash
cd integration_platform
python start_api.py
```

### **Access Points**
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **System Info**: http://localhost:8000/api/system/info

### **Access UI**
- **Web Interface**: http://localhost:3000
- **Login**: Use any credentials (demo mode)

## **Troubleshooting**

### **Event Loop Error**
If you get "Cannot run the event loop while another loop is running":
- Use separate terminals for API and UI servers
- Or run `python start_api.py` and `python start_ui.py` separately

### **Port Conflicts**
- Change ports in `.env` file:
  ```
  API_PORT=8001
  UI_PORT=3001
  ```

### **Import Errors**
- Make sure you're in the `integration_platform` directory
- Run `pip install -r ../requirements.txt`

## **Features Available**
✅ Dashboard with system metrics  
✅ Workflow builder and execution  
✅ Tool browser and execution  
✅ AI assistant for workflow creation  
✅ Real-time WebSocket updates  
✅ JWT authentication  
✅ REST API for all functions  

The platform is ready for use! 🎉
