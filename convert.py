import re
import sys

def convert_drive_link(link):
    # Ekstrak ID file dari link Google Drive
    drive_file_id = None
    
    # Cek pola link dan ekstrak ID file
    match1 = re.search(r'/file/d/([a-zA-Z0-9_-]+)', link)
    match2 = re.search(r'id=([a-zA-Z0-9_-]+)', link)
    
    if match1:
        drive_file_id = match1.group(1)
    elif match2:
        drive_file_id = match2.group(1)
    
    # Jika ID file ditemukan, ubah format link menjadi link unduhan
    if drive_file_id:
        return f"https://drive.google.com/uc?export=download&id={drive_file_id}"
    else:
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_link = sys.argv[1]
        converted_link = convert_drive_link(input_link)
        
        if converted_link:
            print(f"Link yang telah dikonversi: {converted_link}")
        else:
            print("Link Google Drive tidak valid.")
    else:
        print("Silakan masukkan link Google Drive sebagai argumen.")
