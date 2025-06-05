# 导入必要的库
import sys  # 系统相关的功能库
import numpy as np  # 数值计算库，用于数学运算
import pandas as pd  # 数据处理库，用于读取和操作数据
import torch  # PyTorch 深度学习框架
from matplotlib import pyplot as plt  # 可视化库，用于绘制图表

# 读取 CSV 文件到 DataFrame 中，假设文件路径为 "F:/aileanning/data/train.csv"
data = pd.read_csv("F:/aileanning/data/train.csv")

# 获取数据集中每列的众数（mode），用于填充缺失值
modes = data.mode()

# 使用众数填充数据集中缺失的值（NaN）
data.fillna(modes.iloc[0], inplace=True)

# 统计每列中剩余的缺失值数量（理论上应该为 0，因为我们已经填充了缺失值）
data.isna().sum()


# 创建一个新的特征 'LogFare'，它是 'Fare' 列的对数值（加 1 是为了避免 log(0)）
data['LogFare'] = np.log(data['Fare'] + 1)

# 绘制 'LogFare' 列的直方图，并显示该直方图
tmp = data['LogFare'].hist()
plt.show()

# 描述数据集中的非数值列（object 类型）的基本统计信息
ds = data.describe(include=[object])

# 将分类变量（如 'Sex', 'Embarked', 'Pclass'）转换为独热编码（one-hot encoding）
data = pd.get_dummies(data, columns=['Sex', 'Embarked', 'Pclass'])

# 获取所有列名
col = data.columns

# 定义新增的独热编码列名
added_cols = ['Sex_female', 'Sex_male', 'Embarked_C', 'Embarked_Q', 'Embarked_S', 'Pclass_1', 'Pclass_2', 'Pclass_3']

# 将新增的独热编码列的数据类型转换为整数类型
data[added_cols] = data[added_cols].astype(int)

# 打印新增独热编码列的前 5 行数据
s = data[added_cols].head()
print(s)

# 定义独立变量（自变量）列名列表，包括 'Age', 'SibSp', 'Parch', 'LogFare' 和新增的独热编码列
indep_cols = ['Age', 'SibSp', 'Parch', 'LogFare'] + added_cols

# 打印独立变量的前 5 行数据
print(data[indep_cols].head())

# 将目标变量 'Survived' 转换为 PyTorch 张量
t_dep = torch.tensor(data.Survived)

# 将独立变量转换为 PyTorch 张量，并指定数据类型为浮点数
t_indep = torch.tensor(data[indep_cols].values, dtype=torch.float)

# 打印目标变量张量
print(t_dep)

# 设置随机种子以确保结果可复现
torch.manual_seed(442)

# 获取独立变量的特征数量（列数）
n_coeff = t_indep.shape[1]

# 初始化系数张量，使用均匀分布生成随机数，并减去 0.5 使其在 [-0.5, 0.5] 范围内
coeffs = torch.rand(n_coeff) - 0.5

# 打印初始化的系数张量
print(coeffs)

# 计算输入张量与系数张量的乘积，表示线性模型的预测值
mt = t_indep * coeffs

# 打印乘积结果
print(mt)

# 对输入张量进行归一化处理，即每一列除以其最大值
vals, indices = t_indep.max(dim=0)
t_indep = t_indep / vals

# 定义计算预测值的函数
def calc_preds(coffes, indeps):
    # 返回每个样本的预测值，通过系数与输入变量的乘积求和得到
    return (indeps * coffes).sum(dim=1)

# 定义计算损失的函数
def calc_loss(coeffs, indeps, deps):
    # 计算预测值与真实值之间的平均绝对误差（MAE），作为损失函数
    return torch.abs(calc_preds(coeffs, indeps) - deps).mean()

# 使系数张量支持梯度计算，以便后续进行反向传播优化
s = coeffs.requires_grad_()
print(s)

# 计算初始损失
loss = calc_loss(coeffs, t_indep, t_dep)
loss.backward()
with torch.no_grad():
    coeffs.sub_(coeffs.grad * 0.1)
    coeffs.grad.zero_()
    print(calc_loss(coeffs, t_indep, t_dep))

from fastai.data.transforms import RandomSplitter
trn_split,val_split=RandomSplitter(seed=42)(data)
