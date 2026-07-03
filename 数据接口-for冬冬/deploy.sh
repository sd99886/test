#!/bin/bash
# 数据API服务 - 一键部署脚本
# 使用方法：bash deploy.sh

set -e  # 遇到错误立即退出

echo "========================================"
echo "  数据API服务 - 生产环境部署脚本"
echo "========================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置变量
APP_DIR="/opt/data-api"
SERVICE_NAME="data-api"
NGINX_CONF="/etc/nginx/conf.d/data-api.conf"

# 检查是否以root运行
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用 sudo 运行此脚本${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}[1/8] 创建应用目录...${NC}"
mkdir -p $APP_DIR/logs
chown -R root:root $APP_DIR

echo ""
echo -e "${YELLOW}[2/8] 安装Python依赖...${NC}"
cd $APP_DIR
pip3 install -r requirements.txt
pip3 install gunicorn

echo ""
echo -e "${YELLOW}[3/8] 创建日志目录...${NC}"
mkdir -p /var/log/nginx
touch $APP_DIR/logs/access.log
touch $APP_DIR/logs/error.log
chown -R root:root $APP_DIR/logs

echo ""
echo -e "${YELLOW}[4/8] 配置systemd服务...${NC}"
cp data-api.service /etc/systemd/system/$SERVICE_NAME.service
systemctl daemon-reload

echo ""
echo -e "${YELLOW}[5/8] 配置Nginx...${NC}"
cp nginx.conf.example $NGINX_CONF
# 提示用户修改域名
echo -e "${YELLOW}请编辑 $NGINX_CONF 并修改 server_name 为你的域名或IP${NC}"
read -p "按回车继续..."

echo ""
echo -e "${YELLOW}[6/8] 测试Nginx配置...${NC}"
nginx -t

echo ""
echo -e "${YELLOW}[7/8] 启动服务...${NC}"
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME
systemctl restart nginx

echo ""
echo -e "${YELLOW}[8/8] 检查服务状态...${NC}"
sleep 3
systemctl status $SERVICE_NAME --no-pager -l

echo ""
echo "========================================"
echo -e "${GREEN}✓ 部署完成！${NC}"
echo "========================================"
echo ""
echo "访问地址："
echo "  - API文档: http://your-server-ip/"
echo "  - 管理后台: http://your-server-ip/admin"
echo "  - 接口列表: http://your-server-ip/api/queries"
echo ""
echo "常用命令："
echo "  - 查看日志: tail -f $APP_DIR/logs/error.log"
echo "  - 重启服务: systemctl restart $SERVICE_NAME"
echo "  - 停止服务: systemctl stop $SERVICE_NAME"
echo "  - 查看状态: systemctl status $SERVICE_NAME"
echo ""
echo -e "${YELLOW}⚠️  重要提示：${NC}"
echo "  1. 请确保 config.py 已正确配置（AccessKey等）"
echo "  2. 如需HTTPS，请配置SSL证书后启用nginx.conf中的HTTPS部分"
echo "  3. 建议在防火墙中只开放80/443端口，关闭5000端口外部访问"
echo ""
