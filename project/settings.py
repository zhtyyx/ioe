# 媒体文件配置
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 备份配置
BACKUP_ROOT = os.path.join(BASE_DIR, 'backups')
TEMP_DIR = os.path.join(BASE_DIR, 'temp')

# 创建必要的目录
os.makedirs(MEDIA_ROOT, exist_ok=True)
os.makedirs(BACKUP_ROOT, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True) 