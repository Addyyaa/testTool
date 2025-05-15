import torch, numpy as np, pandas as pd
import matplotlib.pyplot as plt
np.set_printoptions(linewidth=140)
torch.set_printoptions(linewidth=140, sci_mode=False, edgeitems=7)
pd.set_option('display.width', 140)

df = pd.read_csv("F:/aileanning/data/train.csv")
ct = df.isna().sum()
print(ct)

modes = df.mode().iloc[0]
print(modes)

df.fillna(modes, inplace=True)
print(df)

ct1 = df.describe(include=np.number)
print(ct1)

df['Fare'].hist()
plt.show()
