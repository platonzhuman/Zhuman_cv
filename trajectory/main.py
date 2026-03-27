import numpy as np
import matplotlib.pyplot as plt
from skimage import measure
from pathlib import Path

def papka():
    path = Path('out')


    # sorted my file
    sort_files = sorted(path.glob('h_*.npy'), key=lambda x: int(x.stem.split('_')[1]))

    all = []
    for i in sort_files:
        img = np.load(i)

        labeled = measure.label(img > 0)
        reg = measure.regionprops(labeled)

        prov_c = []
        for j in reg:
            y, x = j.centroid
            prov_c.append((x, y))
        all.append(prov_c)
    return all


def trajectory(all):

    traject = []

    for prov_c in all:
        for i in prov_c:
            check = False
            for p in traject:
                last_p = p[-1]
                dist = ((i[0]-last_p[0])**2 + (i[1] - last_p[1])**2)**0.5

                if dist < 50:
                    p.append(i)
                    check = True
                    break

            if not check:
                traject.append([i])
    return traject

file = papka()
line = trajectory(file)

plt.figure(figsize=(8, 8))
for k in line:
    x_c = [p[0] for p in k]
    y_c = [p[1] for p in k]
    plt.plot(x_c, y_c, marker='o',  linewidth=1, alpha=0.5) 

plt.title("MY HOME WORK")
plt.show()
