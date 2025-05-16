import requests, os
from .log_factory import LogFactory


def download_log(ip, log_type):
    try:
        # 获取英文文件名
        log_strategy = LogFactory.get_log_strategy(log_type)
        filename = f"{log_strategy.name}.tar.gz"
        url = f"http://{ip}:88/{filename}"
        print(f"正在下载文件: {url}")

        os.makedirs("tmp_log", exist_ok=True)
        local_path = os.path.join("tmp_log", filename)

        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            print(f"文件大小: {total_size / 1024 / 1024:.2f} MB")

            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"下载完成: {local_path}")
            return local_path

    except requests.exceptions.RequestException as e:
        print(f"下载失败: {str(e)}")
        print(f"尝试访问的URL: {url}")
        raise
