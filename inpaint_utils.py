import torch, numpy as np 
from PIL import Image
import cv2 
from typing import List, Dict
    
def resize_if(image, resize_to):
    if image.shape[0]!=resize_to or image.shape[1]!=resize_to:
        image = cv2.resize(src=image, dsize=(resize_to,resize_to), interpolation = cv2.INTER_AREA)
    return image

def make_batch(image, mask, device="cuda:0", resize_to = None):
    image = np.array(Image.open(image).convert("RGB"))
    image = image.astype(np.float32)/255.0
    image = resize_if(image, resize_to)

    image = image[None].transpose(0,3,1,2)
    image = torch.from_numpy(image)

    mask = np.array(Image.open(mask).convert("L"))
    mask = mask.astype(np.float32)/255.0
    mask = resize_if(mask, resize_to)

    mask = mask[None,None]
    mask[mask < 0.5] = 0
    mask[mask >= 0.5] = 1
    mask = torch.from_numpy(mask)
    masked_image = (1-mask)*image

    batch = {"image": image, "mask": mask, "masked_image": masked_image}

    for k in batch:
        batch[k] = batch[k].to(device=device)
        batch[k] = batch[k]*2.0-1.0
    return batch


def seed_everything(seed: int):
    import random, os
    import numpy as np
    import torch
    
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = True

def validate_state_dicts(model_state_dict_1, model_state_dict_2):
    if len(model_state_dict_1) != len(model_state_dict_2):
        print(
            f"Length mismatch: {len(model_state_dict_1)}, {len(model_state_dict_2)}"
        )
        return False

    # Replicate modules have "module" attached to their keys, so strip these off when comparing to local model.
    if next(iter(model_state_dict_1.keys())).startswith("module"):
        model_state_dict_1 = {
            k[len("module") + 1 :]: v for k, v in model_state_dict_1.items()
        }

    if next(iter(model_state_dict_2.keys())).startswith("module"):
        model_state_dict_2 = {
            k[len("module") + 1 :]: v for k, v in model_state_dict_2.items()
        }

    for ((k_1, v_1), (k_2, v_2)) in zip(
        model_state_dict_1.items(), model_state_dict_2.items()
    ):
        if k_1 != k_2:
            print(f"Key mismatch: {k_1} vs {k_2}")
            return False
        # convert both to the same CUDA device
        if str(v_1.device) != "cuda:0":
            v_1 = v_1.to("cuda:0" if torch.cuda.is_available() else "cpu")
        if str(v_2.device) != "cuda:0":
            v_2 = v_2.to("cuda:0" if torch.cuda.is_available() else "cpu")

        if not torch.allclose(v_1, v_2):
            print("different at k_1 %s" % k_1)
            if "model.diffusion_model.out." in k_1:
                print(f"Tensor mismatch: {v_1} vs {v_2}")
            # return False
            

# dict contains the images already
def plot_row_original_mask_output(list_tuple:List[Dict], image_size = 512) -> np.array:
    num_cols = len(list_tuple[0]) # number of keys should be the same in very entry
    num_rows = len(list_tuple) # number elements
    canvas_width = image_size * num_cols
    canvas_height = image_size * num_rows # fixed at one tuple, can be generalized of course

    canvas = np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8)
    
    for row in range(num_rows):
        for col, col_desc in enumerate(list_tuple[row].keys()):
            # Calculate the position where the image should be placed
            x = col * image_size
            y = row * image_size
            
            # Get the corresponding image from the list
            
            img = list_tuple[row][col_desc]
            if col_desc == "mask":
                img = cv2.cvtColor(img,cv2.COLOR_GRAY2RGB)

            # Resize the image to fit in the grid cell
            img = cv2.resize(img, (image_size, image_size))
            
            # Place the image on the canvas at the calculated position
            canvas[y:y+image_size, x:x+image_size, :] = img # cv2.addWeighted(canvas[y:y+image_size, x:x+image_size, :], 0.5, img, 0.5, 0)

    return canvas
    