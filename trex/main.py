import time 
import numpy as np
import mss
import cv2
import pyautogui

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = True


# ================== ^_^
# !!! CONSTANTU !!!
# ================== ^_^

# Для расчета высоты с момента нажатия пробела из параболы прыжка
SAFE_LO_SEC = 0.105
SAFE_HI_SEC = 0.45

# кулдаун для того, чтобы следующий пробел произошел гарантированно 
#  после того, как дино преземлиться
IN_AIR_COOLDOWN = 0.56

#  время держания пробела после нажатия, чтобы не обрезали высоту прыжка
SPACE_HOLD = 0.30

# запас реакции
REACTION_TIME_SEC = 0.033

# процент от ширини дино чтобы избежать случаев, когда при приземлении может
# цыпануть хвост об кактус
DINO_COLLIDE_WIDTH_COEF = 0.95

# оценка скорости от начала, с какой скоростью растет, до макс
FALLBACK_INIT_PPS = 270.0
FALLBACK_ACCEL_PPS = 2.7
FALLBACK_MAX_PPS = 585.0

# тут у нас настройка зрения, дальность обзора, объеденение близких объектов ...
THRESHOLD = 100
MIN_BLOCK_PIXELS = 6
COL_GAP_TO_MERGE = 22
LOOK_AHEAD = 480
GROUND_LINE_OFFSET = 6
# отступ от правого края дино до начала зоны поиска препятствий
OBS_ZONE_GAP = 20
# минимальная ширина блока чтобы считать его препятствием
# настоящий кактус >= 10px, артефакты от руки/тела дино — 1-5px
MIN_OBS_WIDTH = 10

# ================== ^_^
# !!! GLOBALE PER !!!
# ================== ^_^

# когда последний раз нажимали пробел
last_jump = 0.0 

# когда отпустить проел
space_rel = 0.0

# буфер замеров скорости мира + память предыдущего кадра
samples = []
last_f = None
last_w = None
last_t = None

# ================== ^_^
# !!! FUNCTION !!!
# ================== ^_^


# основные проверки: дино в воздухе, в воздухе пробел не жмём пока не приземлиться
def in_air(t=None):
    if t == None:
        t = time.time()
    if t - last_jump < IN_AIR_COOLDOWN:
        return True
    else:
        return False
    
# обновление буфера замера скорости путем сдвига элемента
def upd_speed(cacti, now):
    global last_f, last_w, last_t, samples
    if len(cacti) == 0:
        last_f = None
        last_t = None
        last_w = None
        return
    front = cacti[0]["front"]
    width = cacti[0]["width"]
    if last_f != None and last_t != None and last_w != None:
        # ширина похожа, то такой же кактус
        if abs(width - last_w) <= 5:
            dt = now - last_t
            dd = last_f - front
            if dt > 0 and dt < 0.15 and dd > 0 and dd < 30:
                pps = dd / dt
                if pps > 100 and pps < 1500:
                    samples.append(pps)
                    if len(samples) > 25:
                        samples.pop(0)
    # запоминаем
    last_f = front
    last_w = width
    last_t = now

# возвращение средней скорости мира 
def get_speed():
    n = len(samples)
    if n < 3:
        return None
    s = sorted(samples)
    lo = n // 5
    if lo < 1:
        lo = 1
    hi = n - lo
    if hi - lo <= lo:
        hi = n
    summ = 0
    for x in s[lo:hi]:
        summ = summ + x
    div = hi - lo
    if div < 1:
        div = 1
    return summ / div

# примерная изначальная скорость игры, пока нету реальных замеров :()
def fallback_speed(elapsed):
    sp = FALLBACK_INIT_PPS + FALLBACK_ACCEL_PPS * elapsed
    if sp > FALLBACK_MAX_PPS:
        sp = FALLBACK_MAX_PPS
    return sp

# на случай смены фона с белого на черный и наоборот
def binarize(gray):
    if gray.mean() > 128:
        b = (gray < THRESHOLD).astype(np.uint8)
    else:
        b = (gray > 255 - THRESHOLD).astype(np.uint8)
    b = cv2.erode(b, np.ones((2, 2), np.uint8), iterations=1)
    return b

# ищем динозавра на маске по заданным размерам, выбирая 
# либо ближайшего к курсору кандидата,
#  либо самого левого-верхнего
def find_dino(binary, prefer_near=None):
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cands = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w < 18 or w > 110:
            continue
        if h < 22 or h > 130:
            continue
        r = w / h
        if r < 0.4 or r > 1.8:
            continue
        roi = binary[y:y+h, x:x+w]
        if roi.sum() / float(w * h) < 0.15:
            continue
        cands.append((x, y, w, h))
    if len(cands) == 0:
        return None
    if prefer_near != None:
        px = prefer_near[0]
        py = prefer_near[1]
        # сортировка кандидатов по квадрату расстояния от курсора до центра бокса
        cands.sort(key=lambda b: (b[0] + b[2]/2 - px) ** 2 + (b[1] + b[3]/2 - py) ** 2)
    else:
        cands.sort(key=lambda b: (b[0], b[1]))
    return cands[0]


# функция для нахождения с помощью наведения курсора в браузере дино (вообще четкая тема)
def calibrate(sct):
    print()
    print("^_^ НАВЕДИ КУРСОР МЫШИ НА ДИНОЗАВРА В БРАУЗЕРЕ ^_^")
    i = 5
    while i > 0:
        print("   снимок через " + str(i) + "...")
        time.sleep(1)
        i = i - 1
    mx, my = pyautogui.position()
    print("Курсор: (" + str(mx) + ", " + str(my) + ")")
    monitor = sct.monitors[1]
    # квадратик 400x400
    s = {}
    s["top"] = int(max(monitor["top"], my - 200))
    s["left"] = int(max(monitor["left"], mx - 200))
    s["width"] = int(min(monitor["left"] + monitor["width"], mx + 200) - s["left"])
    s["height"] = int(min(monitor["top"] + monitor["height"], my + 200) - s["top"])
    img = np.array(sct.grab(s))
    gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    binary = binarize(gray)
    cx = mx - s["left"]
    cy = my - s["top"]
    dino = find_dino(binary, prefer_near=(cx, cy))
    if dino == None:
        # сохраняем 
        try:
            cv2.imwrite("calib_debug.png", img)
            cv2.imwrite("calib_debug_bin.png", binary * 255)
        except:
            pass
        return None, None
    x = dino[0]
    y = dino[1]
    w = dino[2]
    h = dino[3]
    # переводим координаты из локальных в абсолютные экранные
    abs_x = s["left"] + x
    abs_y = s["top"] + y
    # теперь делаем большой region вокруг дино с местом справа на 900 px
    # для просмотра препятствий
    region = {}
    region["top"] = int(max(monitor["top"], abs_y - 80))
    region["left"] = int(max(monitor["left"], abs_x - 20))
    region["width"] = int(min(monitor["left"] + monitor["width"], abs_x + 900) - region["left"])
    region["height"] = int(min(monitor["top"] + monitor["height"], abs_y + h + 60) - region["top"])
    return region, (abs_x - region["left"], abs_y - region["top"], w, h)



# эта функция у нас на нахождение препятствий, что-то вроде жесткого анализа
def find_obstacles(binary, dx, dy, dw, dh):
    H = binary.shape[0]
    W = binary.shape[1]
    x1 = dx + dw + OBS_ZONE_GAP
    x2 = x1 + LOOK_AHEAD
    if x2 > W:
        x2 = W
    y_top = dy - int(dh * 0.45)
    if y_top < 0:
        y_top = 0
    y_bot = dy + dh - GROUND_LINE_OFFSET
    if y_bot > H:
        y_bot = H
    if x2 <= x1 or y_bot <= y_top:
        return [], (x1, x2, y_top, y_bot)
    zone = binary[y_top:y_bot, x1:x2]
    col_sums = zone.sum(axis=0)
    obs_idx = np.where(col_sums >= 1)[0]
    if obs_idx.size == 0:
        return [], (x1, x2, y_top, y_bot)
    groups = []
    i = 0
    # склейка узких мест между кактусами
    while i < len(obs_idx):
        front = int(obs_idx[i])
        end = front
        while i < len(obs_idx):
            c = int(obs_idx[i])
            if c <= end + COL_GAP_TO_MERGE:
                end = c
                i = i + 1
            else:
                break
        block = zone[:, front:end+1]
        # отсев слишком мелких блоков 
        if block.sum() < MIN_BLOCK_PIXELS:
            continue
        rows = np.where(block.any(axis=1))[0]
        if rows.size == 0:
            continue
        obs_width = end - front + 1
        # отсев узких артефактов (рука/тело дино, антиалиасинг)
        if obs_width < MIN_OBS_WIDTH:
            continue
        g = {}
        g["front"] = front
        g["end"] = end
        g["width"] = obs_width
        # топ ботон для корректировки того, что за зоной
        g["top"] = int(y_top + rows[0])
        g["bottom"] = int(y_top + rows[-1])
        groups.append(g)
    return groups, (x1, x2, y_top, y_bot)


# понимает что за припятствие и сортирует его
def classify(g, dy, dh):
    bottom = g["bottom"]
    high_line = dy + int(dh * 0.20)
    if bottom < high_line:
        return "bird_high"
    return "cactus"

# эта мега функция = поверх моего ума
# это подбор X, при котором нажать пррбел, да так, чтобы ширина дино была выше 
# при левом крае кактуса = правом пличе дино и наоборот, вообщем потом мы типо 
# из подходящего диапазона выбираем точку ближе к ub - реакция, то есть как можно позже прыгаем ...
def smart_jump(cacti, speed, dw_eff):
    if len(cacti) == 0 or speed == None or speed <= 0:
        return None, [], None
    base = cacti[0]["front"]
    plan = []
    lb = -1e9
    ub = 1e9
    reaction_px = REACTION_TIME_SEC * speed
    for o in cacti:
        offset = o["front"] - base
        # сужаем нижнюю и верхнюю границу х с учётом этого кактуса
        nlb = SAFE_LO_SEC * speed - offset
        if nlb < lb:
            nlb = lb
        nub = SAFE_HI_SEC * speed - o["width"] - dw_eff - offset
        if nub > ub:
            nub = ub
        if nlb > nub:
            break
        lb = nlb
        ub = nub
        plan.append(o)
    if len(plan) == 0:
        # если уже обломились, на удачу пробельнем
        return float(cacti[0]["front"]), [cacti[0]], (None, None)
    target = ub - reaction_px
    if target < lb:
        target = lb
    return float(target), plan, (lb, ub)


# нажимает пробел и фиксирует время пражка
def jump_now():
    global last_jump, space_rel
    now = time.time()
    pyautogui.keyDown("space")
    last_jump = now
    space_rel = now + SPACE_HOLD # когда отпустить + чуть задержка


# проверяет, не пора ли отпустить пробел
def tick_keys():
    global space_rel
    if space_rel > 0:
        if time.time() >= space_rel:
            try:
                pyautogui.keyUp("space")
            except pyautogui.FailSafeException:
                raise
            space_rel = 0.0


# эта мега функция рисут по сути отладочное окно:
# контура, зону поиска, чтобы все аккуратно было и четко )
def draw_debug(gray, dx, dy, dw, dh, zone_box, obstacles, target_x, plan, action, elapsed, fps, sp_est, sp_eff):
    debug = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    x1 = zone_box[0]
    x2 = zone_box[1]
    y_top = zone_box[2]
    y_bot = zone_box[3]
    # бокс дино и зоны поиска
    cv2.rectangle(debug, (dx, dy), (dx + dw, dy + dh), (255, 0, 0), 2)
    cv2.rectangle(debug, (x1, y_top), (x2, y_bot), (0, 200, 0), 1)
    # вертикальная красная линия = X прыжка
    if target_x != None and target_x >= 0:
        tx = x1 + int(target_x)
        cv2.line(debug, (tx, y_top), (tx, y_bot), (0, 0, 255), 2)
        cv2.putText(debug, "X=" + str(int(target_x)), (tx + 3, y_top + 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
    color_map = {}
    color_map["cactus"] = (0, 255, 255)
    color_map["bird_high"] = (160, 160, 160)
    plan_ids = set()
    if plan:
        for o in plan:
            plan_ids.add(id(o))
    for g in obstacles:
        if "kind" in g:
            kind = g["kind"]
        else:
            kind = classify(g, dy, dh)
        if kind in color_map:
            color = color_map[kind]
        else:
            color = (255, 255, 0)
        # объекты которые входят в текущий план прыжка - жирной обводкой
        if id(g) in plan_ids:
            thickness = 3
        else:
            thickness = 1
        ox1 = x1 + g["front"]
        ox2 = x1 + g["end"]
        cv2.rectangle(debug, (ox1, g["top"]), (ox2, g["bottom"]), color, thickness)
        ty = g["top"] - 4
        if ty < 10:
            ty = 10
        cv2.putText(debug, kind + " d=" + str(g["front"]) + " w=" + str(g["width"]),
                    (ox1, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    if sp_est:
        sp_est_str = f"{sp_est:4.0f}"
    else:
        sp_est_str = " -- "
    text1 = f"t={elapsed:5.1f}s fps={fps:4.1f} sp_real={sp_est_str}pps sp_eff={sp_eff:4.0f}pps air={in_air()}"
    cv2.putText(debug, text1, (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    if action:
        cv2.putText(debug, ">>> " + action, (10, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 200), 2)
    return debug




# в этой мега функции всё сразу: тыкаем в экран прячем мышь, чтобы не мешалась и жмем пробел
# далее бесконечный цикл: смотрим на экран ищем кактусы и прыгаем через них
# (высокие птицы игнорим — дино под ними сам пробегает)

def main():
    print("=" * 60)
    print("  T-Rex Bot v5 — empirical speed estimation")
    print("=" * 60)
    sct = mss.mss()
    region, dino_rel = calibrate(sct)
    if region == None:
        print("Не нашёл дино у курсора, см. calib_debug*.png.")
        return
    dx = dino_rel[0]
    dy = dino_rel[1]
    dw = dino_rel[2]
    dh = dino_rel[3]
    print("GAME_REGION = " + str(region))
    print("Дино: x=" + str(dx) + ", y=" + str(dy) + ", w=" + str(dw) + ", h=" + str(dh))

    # клик по центру дино = клик по канвасу = страница ловит фокус
    click_x = region["left"] + dx + dw // 2
    click_y = region["top"] + dy + dh // 2
    pyautogui.click(click_x, click_y)
    monitor = sct.monitors[1]
    # убираем мышь под игру 
    safe_x = region["left"] + region["width"] // 2
    safe_y_a = monitor["top"] + monitor["height"] - 100
    safe_y_b = region["top"] + region["height"] + 200
    if safe_y_a < safe_y_b:
        safe_y = safe_y_a
    else:
        safe_y = safe_y_b
    pyautogui.moveTo(safe_x, safe_y)
    time.sleep(0.20)
    pyautogui.press("space")  # старт игры
    time.sleep(0.5)

    start_time = time.time()
    fps_count = 0
    fps_t0 = start_time
    fps = 0.0
    last_seen = -1
    eff_dw = int(round(dw * DINO_COLLIDE_WIDTH_COEF))
    if eff_dw < 1:
        eff_dw = 1
    print("Эффективная ширина дино для коллизии: " + str(eff_dw) + " px")

    try:
        while True:
            img = np.array(sct.grab(region))
            gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
            binary = binarize(gray)
            elapsed = time.time() - start_time
            tick_keys()  # отпустить пробел если пора
            obstacles, zone_box = find_obstacles(binary, dx, dy, dw, dh)
            # классификация: либо высокая птица (пропускаем), либо кактус (прыгаем)
            cacti = []
            for g in obstacles:
                g["kind"] = classify(g, dy, dh)
                if g["kind"] == "cactus":
                    cacti.append(g)

            now = time.time()
            upd_speed(cacti, now)
            sp_est = get_speed()
            # ээфективная скорость
            if sp_est != None:
                sp_eff = sp_est
            else:
                sp_eff = fallback_speed(elapsed)

            action = None
            target_x = None
            plan = []

            # кактусы
            if len(cacti) > 0 and not in_air():
                target_x, plan, _ = smart_jump(cacti, sp_eff, eff_dw)
                if target_x != None and cacti[0]["front"] <= target_x:
                    action = "JUMP"

            if action == "JUMP":
                jump_now()
                f = cacti[0]
                plan_w = []
                plan_off = []
                for o in plan:
                    plan_w.append(o["width"])
                    plan_off.append(o["front"] - f["front"])
                print(f"[{elapsed:5.1f}s sp={sp_eff:4.0f}pps] JUMP "
                      f"d={f['front']:3d} w={f['width']:3d} "
                      f"target={target_x:5.1f} "
                      f"plan_w={plan_w} plan_off={plan_off}")
            else:
                if len(cacti) > 0:
                    ff = cacti[0]["front"]
                    if ff < 200 and abs(ff - last_seen) > 30:
                        if target_x != None:
                            tx_str = f"{target_x:5.1f}"
                        else:
                            tx_str = "----"
                        print(f"[{elapsed:5.1f}s sp={sp_eff:4.0f}pps] see "
                              f"d={ff:3d} w={cacti[0]['width']:3d} "
                              f"target={tx_str} (air={in_air()})")
                        last_seen = ff

            debug = draw_debug(gray, dx, dy, dw, dh, zone_box, obstacles,
                               target_x, plan, action, elapsed, fps, sp_est, sp_eff)
            # счетчик кадров за секунду
            fps_count = fps_count + 1
            if time.time() - fps_t0 >= 1.0:
                fps = fps_count / (time.time() - fps_t0)
                fps_count = 0
                fps_t0 = time.time()
            cv2.imshow("T-Rex Bot v5 (Q to quit)", debug)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    except pyautogui.FailSafeException:
        # юзер увёл мышь в угол 
        print("FailSafe (мышь в углу).")
    except KeyboardInterrupt:
        pass
    # финальная очистка
    try:
        if space_rel > 0:
            pyautogui.keyUp("space")
    except:
        pass
    cv2.destroyAllWindows()
    print("Готово.")


main()