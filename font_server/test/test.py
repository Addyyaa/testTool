import requests

# 服务器地址
server_url = "http://localhost:8889"

# 获取字体列表
response = requests.get(url=f"{server_url}/api/fonts")
fonts_data = response.json()
font_ttf = fonts_data["fonts"]

# 正确获取字体名称
font_names = list(font_ttf.keys())  # 转换为列表
print("可用字体:", font_names)

# 选择第一个字体
if font_names:
    selected_font = font_names[0]
    font_info = font_ttf[selected_font]
    
    print(f"选择字体: {selected_font}")
    print(f"字体信息: {font_info}")
    
    # 要显示的文字内容
    content = "这是一个文字测试"
    
    # 请求体
    body = {
        "text": content,
        "format": "ttf"
    }
    
    # 创建字体子集
    print(f"\n创建字体子集...")
    print(f"文字内容: {content}")
    print(f"字符数量: {len(set(content))} 个唯一字符")
    
    try:
        response = requests.post(
            url=f"{server_url}/api/font/subset/{selected_font}", 
            json=body,
            timeout=30
        )
        
        if response.status_code == 200:
            font_data = response.content
            size_kb = len(font_data) / 1024
            
            # 保存字体文件
            with open("font_server/test/1.ttf", "wb") as f:
                f.write(font_data)
            
            print(f"✅ 字体子集创建成功!")
            print(f"文件大小: {size_kb:.2f}KB")
            print(f"保存为: test_subset1.ttf")
            
            # 计算压缩比
            original_size = font_info.get('size', 0)
            if original_size > 0:
                compression_ratio = (len(font_data) / original_size) * 100
                print(f"原始大小: {original_size / (1024*1024):.2f}MB")
                print(f"压缩比例: {compression_ratio:.2f}%")
                print(f"节省空间: {(original_size - len(font_data)) / (1024*1024):.2f}MB")
        else:
            print(f"❌ 创建失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        
else:
    print("❌ 没有找到字体文件")