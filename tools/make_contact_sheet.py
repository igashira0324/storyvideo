import os
import argparse
import subprocess
import logging
from typing import List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def make_contact_sheet(images: List[str], output_path: str, grid: str = "5x2"):
    """Creates a contact sheet of images using ffmpeg tile filter."""
    if not images:
        logger.error("No images provided for contact sheet.")
        return False
    
    # Check if all images exist
    valid_images = [img for img in images if os.path.exists(img)]
    if len(valid_images) < len(images):
        logger.warning(f"Only {len(valid_images)}/{len(images)} images found.")
        
    if not valid_images:
        logger.error("No valid images found.")
        return False

    # Construct ffmpeg command
    # -i img1 -i img2 ... -filter_complex "tile=5x2" out.png
    cmd = ["ffmpeg", "-y"]
    for img in valid_images:
        cmd.extend(["-i", img])
    
    cmd.extend([
        "-filter_complex", f"tile={grid}",
        output_path
    ])
    
    try:
        logger.info(f"Creating contact sheet: {output_path} (Grid: {grid})")
        subprocess.run(cmd, capture_output=True, check=True)
        logger.info("Successfully created contact sheet.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed: {e.stderr.decode()}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Create a contact sheet from images")
    parser.add_argument("--project", required=True, help="Project directory")
    parser.add_argument("--pattern", default="assets/shot_*_start.png", help="Image glob pattern relative to project")
    parser.add_argument("--output", default="reports/start_image_contact_sheet.png", help="Output path relative to project")
    parser.add_argument("--grid", default="5x2", help="Tile grid (e.g., 5x2)")
    args = parser.parse_args()

    import glob
    project_dir = os.path.abspath(args.project)
    search_pattern = os.path.join(project_dir, args.pattern)
    image_paths = sorted(glob.glob(search_pattern))
    
    if not image_paths:
        logger.error(f"No images found matching pattern: {search_pattern}")
        return

    output_path = os.path.join(project_dir, args.output)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    make_contact_sheet(image_paths, output_path, args.grid)

if __name__ == "__main__":
    main()
