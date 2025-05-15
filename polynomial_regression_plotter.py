from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
import numpy as np
import matplotlib.pyplot as plt

x = [1, 2, 3]
y = [4, 16, 23]

def plot_poly(degree):
    # 将 x 转换为二维数组
    x_reshaped = np.array(x).reshape(-1, 1)
    model = make_pipeline(PolynomialFeatures(degree), LinearRegression())
    model.fit(x_reshaped, y)

    # 可选：绘制拟合曲线
    x_plot = np.linspace(min(x), max(x), 100).reshape(-1, 1)
    y_plot = model.predict(x_plot)
    plt.scatter(x, y, color='blue', label='Data points')
    plt.plot(x_plot, y_plot, color='red', label=f'Degree {degree} polynomial fit')
    plt.legend()
    plt.show()

plot_poly(2)