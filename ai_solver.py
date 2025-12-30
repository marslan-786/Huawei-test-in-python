import cv2
import numpy as np
import os
import shutil

def get_swap_indices(image_path, rows=2, cols=4, logger=print):
    logger(f"🧠 AI: Analyzing {image_path}")
    
    if not os.path.exists(image_path):
        return 0, 7

    img = cv2.imread(image_path)
    if img is None: return 0, 7

    h, w, _ = img.shape
    tile_h = h // rows
    tile_w = w // cols
    
    # (Tiles slicing logic same as before...)
    debug_dir = "./captures/debug_ai"
    if os.path.exists(debug_dir): shutil.rmtree(debug_dir)
    os.makedirs(debug_dir)
    
    tiles = []
    for r in range(rows):
        for c in range(cols):
            x1 = c * tile_w
            y1 = r * tile_h
            tile = img[y1:y1+tile_h, x1:x1+tile_w]
            tiles.append(tile)
            cv2.imwrite(f"{debug_dir}/tile_{len(tiles)-1}.jpg", tile)

    # (LAB Color and Logic same as V2...)
    tiles_lab = [cv2.cvtColor(t, cv2.COLOR_BGR2LAB) for t in tiles]

    def calculate_connection_error(tile_a, tile_b, direction):
        if direction == 'horizontal':
            edge_a = tile_a[:, -1, :]; edge_b = tile_b[:, 0, :]
        else:
            edge_a = tile_a[-1, :, :]; edge_b = tile_b[0, :, :]
        return np.mean(np.abs(edge_a.astype("int") - edge_b.astype("int")))

    def get_grid_chaos(order):
        total_error = 0
        grid = [order[i:i+cols] for i in range(0, len(order), cols)]
        for r in range(rows):
            for c in range(cols):
                curr_idx = grid[r][c]; curr_tile = tiles_lab[curr_idx]
                if c < cols - 1:
                    right_idx = grid[r][c+1]; right_tile = tiles_lab[right_idx]
                    total_error += calculate_connection_error(curr_tile, right_tile, 'horizontal')
                if r < rows - 1:
                    bot_idx = grid[r+1][c]; bot_tile = tiles_lab[bot_idx]
                    total_error += calculate_connection_error(curr_tile, bot_tile, 'vertical')
        return total_error

    original_order = list(range(rows * cols))
    min_chaos = get_grid_chaos(original_order)
    best_swap = (0, 0)
    
    logger(f"📊 Base Chaos: {min_chaos:.2f}")

    for i in range(len(original_order)):
        for j in range(i + 1, len(original_order)):
            temp_order = original_order[:]
            temp_order[i], temp_order[j] = temp_order[j], temp_order[i]
            chaos = get_grid_chaos(temp_order)
            if chaos < min_chaos:
                # logger(f"💡 Better Match: {i} <-> {j} (Score: {chaos:.2f})") # Too noisy for UI
                min_chaos = chaos
                best_swap = (i, j)

    source, target = best_swap
    
    # Save Preview
    final_order = original_order[:]
    if source != target: final_order[source], final_order[target] = final_order[target], final_order[source]
    
    # Rebuild
    grid_idx = [final_order[i:i+cols] for i in range(0, len(final_order), cols)]
    final_rows = []
    for r in range(rows):
        row_tiles = []
        for c in range(cols): row_tiles.append(tiles[grid_idx[r][c]])
        final_rows.append(np.hstack(row_tiles))
    
    solved_img = np.vstack(final_rows)
    cv2.imwrite("./captures/ai_solved_preview.jpg", solved_img)
    
    logger(f"📢 AI DECISION: Swap {source} <-> {target}")
    return source, target