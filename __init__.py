import folder_paths
import os
import requests
import json
import base64
from PIL import Image
import numpy as np
from comfy.cli_args import args
from nodes import PngInfo

class Webhook:
    """
    Handles saving generated images and sending webhook notifications.
    This node saves the output images and sends them to a specified webhook endpoint
    for further processing or notification purposes.
    """
    
    def __init__(self):
        self.save_directory = folder_paths.get_output_directory()
        self.asset_type = "output"
        self.name_prefix = ""
        self.png_compression = 4

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "ComfyUI"}),
                "webhook_url": ("STRING", {"default": "", "placeholder": "enter webhook URL"}),
            },
            "optional": {
                "metadata": ("STRING", {"default": "", "placeholder": "enter metadata for webhook"}),
                "external_uid": ("STRING", {"default": "", "placeholder": "enter external uid of generated image or session"}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    CATEGORY = "image/Save Image & Notify"
    FUNCTION = "process_and_notify"
    RETURN_TYPES = ()
    OUTPUT_NODE = True

    def process_and_notify(
        self,
        images,
        filename_prefix="ComfyUI",
        webhook_url="",
        metadata="",
        external_uid="",
        prompt=None,
        extra_pnginfo=None,
    ):
        custom_metadata = metadata
        
        # Handle image saving
        output_name = filename_prefix + self.name_prefix
        save_path, base_name, img_counter, sub_path, final_prefix = folder_paths.get_save_image_path(
            output_name, 
            self.save_directory, 
            images[0].shape[1], 
            images[0].shape[0]
        )
        
        saved_files = []
        for idx, img_data in enumerate(images):
            # Convert tensor to image
            img_array = 255. * img_data.cpu().numpy()
            output_img = Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8))
            
            # Prepare metadata if enabled
            img_metadata = None
            if not args.disable_metadata:
                img_metadata = PngInfo()
                if prompt:
                    img_metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo:
                    for key, value in extra_pnginfo.items():
                        img_metadata.add_text(key, json.dumps(value))

            # Generate unique filename
            current_name = base_name.replace("%batch_num%", str(idx))
            img_filename = f"{current_name}_{img_counter:05}_.png"
            full_path = os.path.join(save_path, img_filename)
            
            # Save the image
            output_img.save(
                full_path,
                pnginfo=img_metadata,
                compress_level=self.png_compression
            )
            
            saved_files.append({
                "filename": img_filename,
                "subfolder": sub_path,
                "type": self.asset_type
            })
            img_counter += 1

        print(f"Successfully saved images: {saved_files}")

        # Send webhook notification
        webhook_data = {
            "metadata": custom_metadata,
            "external_uid": external_uid,
            "images": json.dumps(saved_files)
        }
        print(f"Preparing webhook data: {webhook_data}")

        # Send the last image as attachment
        webhook_response = requests.post(
            webhook_url,
            data=webhook_data,
            files={"file": open(full_path, "rb")}
        )

        if webhook_response.status_code >= 300:
            print(f"Webhook notification failed - Status: {webhook_response.status_code}, Response: {webhook_response.text}")

        return {"ui": {"images": saved_files}}


# Node registration
NODE_CLASS_MAPPINGS = {
    "Webhook": Webhook,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Webhook": "Webhook Image Saver",
}

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "Webhook",
]