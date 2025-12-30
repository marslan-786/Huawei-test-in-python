import cv2
import numpy as np
import os
import shutil

def get_swap_indices(image_path, rows=2, cols=4):
    print(f"\n🧠 AI V2 (Human Vision): Analyzing {image_path}")
    
    if not os.path.exists(image_path):
        print("❌ AI ERROR: Image file missing!")
        return 0, 0

    # 1. Load Image
    img = cv2.imread(image_path)
    if img is None: return 0, 0

    h, w, _ = img.shape
    tile_h = h // rows
    tile_w = w // cols
    
    # Debug Directory
    debug_dir = "./captures/debug_ai"
    if os.path.exists(debug_dir): shutil.rmtree(debug_dir)
    os.makedirs(debug_dir)

    # 2. Slice Tiles
    tiles = []
    for r in range(rows):
        for c in range(cols):
            x1 = c * tile_w
            y1 = r * tile_h
            tile = img[y1:y1+tile_h, x1:x1+tile_w]
            tiles.append(tile)

    # 3. CONVERT TO LAB COLOR SPACE (Better for human-like perception)
    # RGB fails on snow/clouds. LAB separates Lightness from Color.
    tiles_lab = [cv2.cvtColor(t, cv2.COLOR_BGR2LAB) for t in tiles]

    def calculate_connection_error(tile_a, tile_b, direction):
        """
        Calculates how badly two tiles match at their connecting edge.
        direction 'horizontal': A is Left, B is Right
        direction 'vertical': A is Top, B is Bottom
        """
        # We focus heavily on the matching pixels at the border
        if direction == 'horizontal':
            edge_a = tile_a[:, -1, :] # Right column of A
            edge_b = tile_b[:, 0, :]  # Left column of B
        else:
            edge_a = tile_a[-1, :, :] # Bottom row of A
            edge_b = tile_b[0, :, :]  # Top row of B
            
        # Calculate difference using LAB colors
        diff = np.mean(np.abs(edge_a.astype("int") - edge_b.astype("int")))
        return diff

    def get_grid_chaos(order):
        total_error = 0
        grid = [order[i:i+cols] for i in range(0, len(order), cols)]
        
        for r in range(rows):
            for c in range(cols):
                curr_idx = grid[r][c]
                curr_tile = tiles_lab[curr_idx]
                
                # Check Right
                if c < cols - 1:
                    right_idx = grid[r][c+1]
                    right_tile = tiles_lab[right_idx]
                    total_error += calculate_connection_error(curr_tile, right_tile, 'horizontal')
                
                # Check Bottom
                if r < rows - 1:
                    bot_idx = grid[r+1][c]
                    bot_tile = tiles_lab[bot_idx]
                    total_error += calculate_connection_error(curr_tile, bot_tile, 'vertical')
                    
        return total_error

    # 4. Find Best Swap
    original_order = list(range(rows * cols))
    min_chaos = get_grid_chaos(original_order)
    best_swap = (0, 0)
    
    print(f"📊 Base Chaos: {min_chaos:.2f}")

    for i in range(len(original_order)):
        for j in range(i + 1, len(original_order)):
            # Create Swap
            temp_order = original_order[:]
            temp_order[i], temp_order[j] = temp_order[j], temp_order[i]
            
            chaos = get_grid_chaos(temp_order)
            
            # Logic: Improvement must be noticeable (> 5.0 score diff)
            if chaos < min_chaos:
                print(f"💡 Better Match: {i} <-> {j} (Score: {chaos:.2f})")
                min_chaos = chaos
                best_swap = (i, j)

    source, target = best_swap
    
    # 5. GENERATE PREVIEW IMAGE (To Verify Truth)
    # AI will reconstruct the image based on its decision
    final_order = original_order[:]
    if source != target:
        final_order[source], final_order[target] = final_order[target], final_order[source]
    
    # Rebuild image
    final_rows = []
    grid_idx = [final_order[i:i+cols] for i in range(0, len(final_order), cols)]
    
    for r in range(rows):
        row_tiles = []
        for c in range(cols):
            row_tiles.append(tiles[grid_idx[r][c]])
        final_rows.append(np.hstack(row_tiles))
    
    solved_img = np.vstack(final_rows)
    preview_path = "./captures/ai_solved_preview.jpg"
    cv2.imwrite(preview_path, solved_img)
    
    print(f"🖼️ PREVIEW SAVED: {preview_path} (Check this to trust AI)")
    print(f"📢 FINAL DECISION: Swap {source} <-> {target}")
    
    return source, target