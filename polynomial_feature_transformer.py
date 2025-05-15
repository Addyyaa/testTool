from sklearn.preprocessing import PolynomialFeatures
import numpy as np, matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline

# 原始数据
x = np.array([1, 2, 3, 4]).reshape(-1, 1)  # 将 x 转换为二维数组
y = np.array([4, 16, 27,33]).reshape(-1, 1)
model = make_pipeline(PolynomialFeatures(3), LinearRegression())

model.fit(x, y)
plt.scatter(x, y)
plt.plot(x, model.predict(x))

