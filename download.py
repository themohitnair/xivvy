import os
import time
from process.dataset import DatasetDownloader

if __name__ == "__main__":
    total_start_time = time.perf_counter()

    json_file_path = os.path.join("data", "arxiv-metadata-oai-snapshot.json")
    if os.path.exists(json_file_path):
        print(f"Removing previous {json_file_path}...")
        os.remove(json_file_path)
        print(f"Previous {json_file_path} removed successfully.")
    else:
        print(f"No previous {json_file_path} found.")

    DatasetDownloader().download()
    total_elapsed_time = time.perf_counter() - total_start_time
    print(f"\nTotal operation completed in {total_elapsed_time:.2f} seconds.")
