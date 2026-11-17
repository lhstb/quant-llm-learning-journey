@echo off
chcp 65001 >nul
echo =======================================
echo 正在检查并安装依赖 (openai, python-dotenv)...
pip install openai python-dotenv
echo.
echo 正在启动大模型测试脚本...
python w1_api_test.py
echo.
echo 运行结束！
pause