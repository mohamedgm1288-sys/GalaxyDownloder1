from flask import Flask, request, jsonify, send_file, send_from_directory, after_this_request
import yt_dlp
import os
import uuid
import subprocess
import requests

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024 

# حط الـ API Token بتاعك هنا بين العلامتين
AUDD_API_TOKEN = "b8ef965c319c1484138dad686a5a234f"

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# 1. البحث
@app.route('/search')
def search_song():
    q = request.args.get('q')
    if not q: return jsonify({"error": "مفيش بحث"}), 400
    try:
        ydl_opts = {'extract_flat': True, 'quiet': True, 'no_warnings': True, 'playlist_items': '1-6'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch6:{q}", download=False)
            results = []
            if 'entries' in info:
                for entry in info['entries']:
                    dur = entry.get('duration', 0)
                    vid_id = entry.get('id')
                    thumb = entry.get('thumbnail') or f"https://i.ytimg.com/vi/{vid_id}/mqdefault.jpg"
                    results.append({
                        'title': entry.get('title', 'Unknown'),
                        'duration': f"{dur//60}:{dur%60:02d}" if dur else "N/A",
                        'thumbnail': thumb,
                        'url': f"https://www.youtube.com/watch?v={vid_id}"
                    })
            return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 2. جلب معلومات الرابط (للمعاينة والمشاهدة)
@app.route('/info')
def get_info():
    url = request.args.get('url')
    if not url: return jsonify({"error": "مفيش رابط"}), 400
    try:
        ydl_opts = {'quiet': True, 'no_warnings': True, 'format': 'best[height<=480][ext=mp4]/best'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            dur = info.get('duration', 0)
            return jsonify({
                'title': info.get('title', 'فيديو غير معروف'),
                'duration': f"{dur//60}:{dur%60:02d}" if dur else "N/A",
                'thumbnail': info.get('thumbnail', ''),
                'preview_url': info.get('url', ''), # رابط الفيديو المباشر للمشاهدة
                'url': url
            })
    except Exception as e:
        return jsonify({"error": "الرابط غير مدعوم"}), 500

# 3. التحميل (من رابط مباشر)
@app.route('/download')
def download():
    url = request.args.get('url')
    format_type = request.args.get('type', 'audio')
    if not url: return "الرابط مفقود", 400

    file_id = str(uuid.uuid4())
    out_template = f"{file_id}.%(ext)s"
    
    if format_type == 'audio':
        ydl_opts = {'format': 'bestaudio/best', 'outtmpl': out_template, 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}], 'quiet': True, 'no_warnings': True}
        ext, media_type = 'mp3', 'audio/mpeg'
    else:
        ydl_opts = {'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 'merge_output_format': 'mp4', 'outtmpl': out_template, 'quiet': True, 'no_warnings': True}
        ext, media_type = 'mp4', 'video/mp4'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'media').replace('/', '_').replace('\\', '_')
            filename = f"{file_id}.{ext}"
            if not os.path.exists(filename):
                for f in os.listdir('.'):
                    if f.startswith(file_id) and f.endswith(f'.{ext}'):
                        filename = f; break
            @after_this_request
            def remove_file(response):
                try: os.remove(filename)
                except: pass
                return response
            return send_file(filename, as_attachment=True, download_name=f"{title}.{ext}", mimetype=media_type)
    except Exception as e:
        return f"حصل مشكلة: {str(e)}", 500

# 4. التحميل بالاسم (للأغاني اللي Shazam بيلاقيها)
@app.route('/download_search')
def download_search():
    query = request.args.get('q')
    format_type = request.args.get('type', 'audio')
    if not query: return "مفيش بحث", 400
    
    file_id = str(uuid.uuid4())
    out_template = f"{file_id}.%(ext)s"
    
    if format_type == 'audio':
        ydl_opts = {'format': 'bestaudio/best', 'outtmpl': out_template, 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}], 'quiet': True, 'no_warnings': True, 'noplaylist': True}
        ext, media_type = 'mp3', 'audio/mpeg'
    else:
        ydl_opts = {'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 'merge_output_format': 'mp4', 'outtmpl': out_template, 'quiet': True, 'no_warnings': True, 'noplaylist': True}
        ext, media_type = 'mp4', 'video/mp4'

    try:
        # بندور على أول نتيجة وننزلها
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=True)
            if 'entries' in info:
                info = info['entries'][0] # أول نتيجة
            title = info.get('title', 'media').replace('/', '_').replace('\\', '_')
            filename = f"{file_id}.{ext}"
            if not os.path.exists(filename):
                for f in os.listdir('.'):
                    if f.startswith(file_id) and f.endswith(f'.{ext}'):
                        filename = f; break
            @after_this_request
            def remove_file(response):
                try: os.remove(filename)
                except: pass
                return response
            return send_file(filename, as_attachment=True, download_name=f"{title}.{ext}", mimetype=media_type)
    except Exception as e:
        return f"حصل مشكلة: {str(e)}", 500

# 5. تحويل فيديو محلي
@app.route('/convert', methods=['POST'])
def convert_local():
    if 'video' not in request.files: return "مفيش ملف", 400
    file = request.files['video']
    file_id = str(uuid.uuid4())
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'mp4'
    input_file = f"{file_id}_input.{ext}"
    output_file = f"{file_id}_output.mp3"
    file.save(input_file)
    try:
        cmd = ['ffmpeg', '-i', input_file, '-vn', '-acodec', 'libmp3lame', '-q:a', '2', output_file]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        @after_this_request
        def cleanup(response):
            try: os.remove(input_file); os.remove(output_file)
            except: pass
            return response
        return send_file(output_file, as_attachment=True, download_name="audio.mp3", mimetype="audio/mpeg")
    except:
        return "فشل التحويل", 500

# 6. التعرف على الأغنية
@app.route('/recognize', methods=['POST'])
def recognize_song():
    if AUDD_API_TOKEN == "ضع_التوكن_بتاعك_هنا":
        return jsonify({"found": False, "message": "لازم تحط الـ API Token الأول في الكود."})

    if 'media' not in request.files: return jsonify({"error": "مفيش ملف"}), 400
    file = request.files['media']
    file_id = str(uuid.uuid4())
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'mp4'
    input_file = f"{file_id}_rec_input.{ext}"
    audio_file = f"{file_id}_rec_audio.mp3"
    file.save(input_file)

    try:
        cmd = ['ffmpeg', '-y', '-i', input_file, '-vn', '-acodec', 'libmp3lame', '-q:a', '5', audio_file]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with open(audio_file, 'rb') as f:
            response = requests.post('https://api.audd.io/', data={'api_token': AUDD_API_TOKEN, 'return': 'spotify'}, files={'file': f})
        result = response.json()
        os.remove(input_file); os.remove(audio_file)

        if result.get('status') == 'success' and result.get('result'):
            track = result['result']
            img = ''
            if 'spotify' in track and 'album' in track['spotify'] and 'images' in track['spotify']['album']:
                img = track['spotify']['album']['images'][0]['url']
            return jsonify({"found": True, "title": track.get('title', 'غير معروف'), "artist": track.get('artist', 'غير معروف'), "image": img})
        else:
            return jsonify({"found": False, "message": "مقدرتش أتعرف على الأغنية دي."})
    except Exception as e:
        if os.path.exists(input_file): os.remove(input_file)
        if os.path.exists(audio_file): os.remove(audio_file)
        return jsonify({"found": False, "message": f"حدث خطأ."})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
