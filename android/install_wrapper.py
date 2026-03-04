import urllib.request
import zipfile
import io
import os

url = 'https://services.gradle.org/distributions/gradle-8.5-bin.zip'
print('Downloading gradle 8.5 to extract wrapper...')

# We just need gradle-wrapper.jar.
try:
    with urllib.request.urlopen(url) as response:
        with zipfile.ZipFile(io.BytesIO(response.read())) as z:
            for info in z.infolist():
                if info.filename.endswith('gradle-wrapper-8.5.jar') or info.filename.endswith('gradle-wrapper.jar'):
                    print(f"Found wrapper: {info.filename}")
                    content = z.read(info.filename)
                    # Write to the destination
                    dest = os.path.join('gradle', 'wrapper', 'gradle-wrapper.jar')
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with open(dest, 'wb') as f:
                        f.write(content)
                    print(f"Extracted wrapper to {dest}")
                    break
except Exception as e:
    print(f"Failed: {e}")

