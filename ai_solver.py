import cv2
import numpy as np
import math

def get_swap_indices(image_path, rows=2, cols=4):
    print(f"🧠 AI: Analyzing Image {image_path}...")
    
    # 1. Load Image
    img = cv2.imread(image_path)
    if img is None:
        print("❌ AI: Image not found/unreadable")
        return 0, 0 # Fail safe

    h, w, _ = img.shape
    tile_h = h // rows
    tile_w = w // cols
    
    # 2. Slice Image into 8 Tiles
    tiles = []
    for r in range(rows):
        for c in range(cols):
            x1 = c * tile_w
            y1 = r * tile_h
            # Extract tile
            tile = img[y1:y1+tile_h, x1:x1+tile_w]
            tiles.append(tile)
            
    # 3. Define Error Function (Edge Matching)
    # Hum check karenge k tile A ka right border tile B k left border se kitna milta hai
    def calculate_error(current_order):
        total_error = 0
        
        # Grid reconstruction based on current order
        grid = [current_order[i:i+cols] for i in range(0, len(current_order), cols)]
        
        for r in range(rows):
            for c in range(cols):
                idx = grid[r][c]
                current_tile = tiles[idx]
                
                # Check Right Neighbor error
                if c < cols - 1:
                    right_idx = grid[r][c+1]
                    right_tile = tiles[right_idx]
                    # Compare: Current Right Column vs Neighbor Left Column
                    diff = np.mean(np.abs(current_tile[:, -1] - right_tile[:, 0]))
                    total_error += diff

                # Check Bottom Neighbor error
                if r < rows - 1:
                    bottom_idx = grid[r+1][c]
                    bottom_tile = tiles[bottom_idx]
                    # Compare: Current Bottom Row vs Neighbor Top Row
                    diff = np.mean(np.abs(current_tile[-1, :] - bottom_tile[0, :]))
                    total_error += diff
                    
        return total_error

    # 4. Brute Force Logic (Try Swapping Every Pair)
    # Since only 1 pair is swapped, we check all combinations.
    # Total tiles = 8. Combinations = 28. Very fast.
    
    original_order = list(range(rows * cols))
    min_error = float('inf')
    best_swap = (0, 0) # Default (No swap)
    
    # Initial error (Current messy state)
    base_error = calculate_error(original_order)
    print(f"📊 Initial Chaos Score: {base_error:.2f}")

    # Loop through all pairs (i, j)
    for i in range(len(original_order)):
        for j in range(i + 1, len(original_order)):
            # Create a temporary swapped order
            temp_order = original_order[:]
            temp_order[i], temp_order[j] = temp_order[j], temp_order[i]
            
            # Check error for this swap
            err = calculate_error(temp_order)
            
            if err < min_error:
                min_error = err
                best_swap = (i, j)

    # 5. Conclusion
    source, target = best_swap
    
    # Validation: Error must significantly drop to justify a swap
    improvement = base_error - min_error
    print(f"✅ AI Found Best Swap: Tile {source} <-> Tile {target} (Error: {min_error:.2f})")
    
    if improvement < 5: # Threshold logic
        print("⚠️ No significant improvement found (Maybe already solved?)")
        return 0, 0
        
    return source, target