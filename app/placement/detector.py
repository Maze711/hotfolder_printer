from collections import deque


def _detect_black_placeholders(template, threshold=25, min_pixels=2500):
    if threshold < 0 or threshold > 255:
        raise ValueError("black threshold must be in range 0-255")
    if min_pixels <= 0:
        raise ValueError("black_min_pixels must be > 0")

    gray = template.convert("L")
    width, height = gray.size
    pixels = gray.tobytes()
    total = width * height
    visited = bytearray(total)

    def is_black(index):
        return pixels[index] <= threshold

    components = []

    for idx in range(total):
        if visited[idx] or not is_black(idx):
            continue

        queue = deque([idx])
        visited[idx] = 1
        count = 0

        start_x = idx % width
        start_y = idx // width
        min_x = max_x = start_x
        min_y = max_y = start_y

        while queue:
            current = queue.popleft()
            x = current % width
            y = current // width
            count += 1

            if x < min_x:
                min_x = x
            if x > max_x:
                max_x = x
            if y < min_y:
                min_y = y
            if y > max_y:
                max_y = y

            if x > 0:
                left = current - 1
                if not visited[left] and is_black(left):
                    visited[left] = 1
                    queue.append(left)

            if x < width - 1:
                right = current + 1
                if not visited[right] and is_black(right):
                    visited[right] = 1
                    queue.append(right)

            if y > 0:
                up = current - width
                if not visited[up] and is_black(up):
                    visited[up] = 1
                    queue.append(up)

            if y < height - 1:
                down = current + width
                if not visited[down] and is_black(down):
                    visited[down] = 1
                    queue.append(down)

        if count >= min_pixels:
            components.append(
                {
                    "x": min_x,
                    "y": min_y,
                    "width": (max_x - min_x) + 1,
                    "height": (max_y - min_y) + 1,
                    "pixels": count,
                }
            )

    components.sort(key=lambda c: (c["y"], c["x"]))
    return components
