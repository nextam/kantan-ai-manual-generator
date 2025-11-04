#!/bin/bash

# ログファイル
LOGFILE="/var/log/cloudwatch-setup.log"
exec > >(tee -a $LOGFILE)
exec 2>&1

echo "$(date): CloudWatch エージェント設定開始"

# システムアップデート
apt-get update -y
apt-get upgrade -y

# SSM Agent インストール（Ubuntu 20.04+では通常プリインストールされているが、確認のため）
snap install amazon-ssm-agent --classic
systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service
systemctl start snap.amazon-ssm-agent.amazon-ssm-agent.service

# CloudWatch エージェントダウンロードとインストール
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
dpkg -i -E ./amazon-cloudwatch-agent.deb

# CloudWatch エージェント設定ファイルを作成
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
    "agent": {
        "metrics_collection_interval": 60,
        "run_as_user": "cwagent"
    },
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/home/ubuntu/manual_generator/app.log",
                        "log_group_name": "/aws/ec2/manual-generator",
                        "log_stream_name": "{instance_id}/manual-generator",
                        "timezone": "Asia/Tokyo"
                    },
                    {
                        "file_path": "/home/ubuntu/operation_analysis/*.log",
                        "log_group_name": "/aws/ec2/operation-analysis",
                        "log_stream_name": "{instance_id}/operation-analysis",
                        "timezone": "Asia/Tokyo"
                    },
                    {
                        "file_path": "/var/log/syslog",
                        "log_group_name": "/aws/ec2/system",
                        "log_stream_name": "{instance_id}/syslog",
                        "timezone": "Asia/Tokyo"
                    }
                ]
            }
        }
    },
    "metrics": {
        "namespace": "CWAgent",
        "metrics_collected": {
            "cpu": {
                "measurement": [
                    "cpu_usage_idle",
                    "cpu_usage_iowait",
                    "cpu_usage_user",
                    "cpu_usage_system"
                ],
                "metrics_collection_interval": 60,
                "totalcpu": false
            },
            "disk": {
                "measurement": [
                    "used_percent"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "diskio": {
                "measurement": [
                    "io_time"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "mem": {
                "measurement": [
                    "mem_used_percent"
                ],
                "metrics_collection_interval": 60
            }
        }
    }
}
EOF

# CloudWatch エージェント開始
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# ログディレクトリの権限設定
mkdir -p /home/ubuntu/manual_generator
mkdir -p /home/ubuntu/operation_analysis
touch /home/ubuntu/manual_generator/app.log
chown ubuntu:ubuntu /home/ubuntu/manual_generator/app.log
chown ubuntu:ubuntu /home/ubuntu/operation_analysis/

echo "$(date): CloudWatch エージェント設定完了"
