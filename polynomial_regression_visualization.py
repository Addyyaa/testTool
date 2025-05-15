import numpy as np
import matplotlib.pyplot as plt

# 参数设置（与你的代码一致）
total_steps = 90  # 总步数（基于之前的例子：3 个 epoch，每个 epoch 30 步）
warmup_ratio = 0.1  # 预热比例
initial_lr = 2e-5  # 初始学习率（假设值）
min_lr = 0  # 最小学习率（余弦调度器的终点）

# 计算预热步数
warmup_steps = int(total_steps * warmup_ratio)  # 前 10% 步数用于预热
print(f"预热步数: {warmup_steps}")

# 计算学习率变化
learning_rates = []
for step in range(total_steps):
    if step < warmup_steps:
        # 预热阶段：学习率从 0 线性增加到 initial_lr
        lr = initial_lr * (step / warmup_steps)
    else:
        # 余弦调度器阶段：从 initial_lr 衰减到 min_lr
        # 公式：lr = min_lr + 0.5 * (initial_lr - min_lr) * (1 + cos(pi * t))
        t = (step - warmup_steps) / (total_steps - warmup_steps)  # 余弦衰减的进度
        lr = min_lr + 0.5 * (initial_lr - min_lr) * (1 + np.cos(np.pi * t))
    learning_rates.append(lr)

# 绘制学习率变化曲线
plt.figure(figsize=(10, 6))
plt.plot(range(total_steps), learning_rates, label='Learning Rate')
plt.axvline(x=warmup_steps, color='r', linestyle='--', label='Warmup End')
plt.title('Learning Rate Schedule (Warmup + Cosine Annealing)')
plt.xlabel('Training Steps')
plt.ylabel('Learning Rate')
plt.grid(True)
plt.legend()
plt.show()
