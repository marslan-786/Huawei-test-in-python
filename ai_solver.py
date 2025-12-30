import cv2
import numpy as np
import os
import shutil

def get_swap_indices(image_path, rows=2, cols=4):
    print(f"\n🧠 AI START: Analyzing {image_path}")
    
    if not os.path.exists(image_path):
        print("❌ AI ERROR: Image file does not exist!")
        return 0, 7 # Fail safe force move

    # 1. Load Image
    img = cv2.imread(image_path)
    if img is None:
        print("❌ AI ERROR: OpenCV could not read image!")
        return 0, 7

    h, w, _ = img.shape
    print(f"📏 Image Size: {w}x{h}")
    
    tile_h = h // rows
    tile_w = w // cols
    
    # Debug Folder for Tiles
    debug_dir = "./captures/debug_tiles"
    if os.path.exists(debug_dir): shutil.rmtree(debug_dir)
    os.makedirs(debug_dir)

    # 2. Slice Image
    tiles = []
    print("✂️ Slicing Image into tiles...")
    for r in range(rows):
        for c in range(cols):
            x1 = c * tile_w
            y1 = r * tile_h
            tile = img[y1:y1+tile_h, x1:x1+tile_w]
            tiles.append(tile)
            
            # Save for visual verify
            idx = len(tiles) - 1
            cv2.imwrite(f"{debug_dir}/tile_{idx}.jpg", tile)

    print(f"✅ Saved 8 tiles in {debug_dir}. Check them!")

    # 3. Simple Edge Matching Logic
    def calculate_score(idx_list):
        score = 0
        # Reconstruct grid virtually
        grid = [idx_list[i:i+cols] for i in range(0, len(idx_list), cols)]
        
        for r in range(rows):
            for c in range(cols):
                current_idx = grid[r][c]
                curr_tile = tiles[current_idx]
                
                # Compare with Right Neighbor
                if c < cols - 1:
                    right_idx = grid[r][c+1]
                    right_tile = tiles[right_idx]
                    # Right edge of current vs Left edge of next
                    diff = np.mean(np.abs(curr_tile[:, -1] - right_tile[:, 0]))
                    score += diff
                
                # Compare with Bottom Neighbor
                if r < rows - 1:
                    bottom_idx = grid[r+1][c]
                    bottom_tile = tiles[bottom_idx]
                    # Bottom edge of current vs Top edge of next
                    diff = np.mean(np.abs(curr_tile[-1, :] - bottom_tile[0, :]))
                    score += diff
        return score

    # 4. Find Best Swap
    original_indices = list(range(rows * cols))
    best_score = calculate_score(original_indices)
    best_swap = (0, 0) # Default: No swap
    
    print(f"📊 Initial Chaos Score: {best_score:.2f}")

    # Check all pairs
    found_better = False
    for i in range(len(original_indices)):
        for j in range(i + 1, len(original_indices)):
            # Swap virtually
            temp_indices = original_indices[:]
            temp_indices[i], temp_indices[j] = temp_indices[j], temp_indices[i]
            
            new_score = calculate_score(temp_indices)
            
            # If significant improvement
            if new_score < best_score:
                print(f"💡 Potential Swap Found: {i} <-> {j} (Score: {new_score:.2f})")
                best_score = new_score
                best_swap = (i, j)
                found_better = True

    source, target = best_swap
    
    if source == target:
        print("⚠️ AI WARNING: No swap improved the image. Logic thinks image is perfect.")
        print("🔨 FORCE MODE: Returning 0 -> 4 to test movement.")
        return 0, 4
    
    print(f"📢 AI FINAL DECISION: Swap Tile {source} with Tile {target}")
    return source, target