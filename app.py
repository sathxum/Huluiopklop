from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
from pytubefix import YouTube
import os
import tempfile

app = Flask(__name__)
CORS(app)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Downloader</title>
    <style>
        body { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            font-family: 'Segoe UI', sans-serif; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            min-height: 100vh; 
            margin: 0; 
            color: white;
        }
        .container { 
            background: rgba(255,255,255,0.1); 
            backdrop-filter: blur(10px);
            padding: 40px; 
            border-radius: 20px; 
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            max-width: 600px;
            width: 90%;
        }
        h1 { text-align: center; margin-bottom: 30px; }
        input[type="text"] { 
            width: 100%; 
            padding: 15px; 
            border: none; 
            border-radius: 10px; 
            margin-bottom: 20px;
            font-size: 16px;
        }
        button { 
            width: 100%; 
            padding: 15px; 
            background: #ff4757; 
            color: white; 
            border: none; 
            border-radius: 10px; 
            font-size: 18px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover { transform: translateY(-2px); background: #ff6b81; }
        .video-info { margin-top: 20px; }
        .stream-btn {
            background: rgba(255,255,255,0.2);
            margin: 5px 0;
            text-align: left;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .thumbnail { width: 100%; border-radius: 10px; margin-bottom: 15px; }
        .loading { text-align: center; display: none; }
        .error { color: #ff6b6b; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 YouTube Downloader</h1>
        <input type="text" id="url" placeholder="Paste YouTube URL here..." />
        <button onclick="fetchVideo()">Fetch Video</button>
        <div class="loading" id="loading">Loading...</div>
        <div id="result"></div>
    </div>
    <script>
        async function fetchVideo() {
            const url = document.getElementById('url').value;
            if (!url) return alert('Enter URL');
            document.getElementById('loading').style.display = 'block';
            document.getElementById('result').innerHTML = '';
            try {
                const res = await fetch('/api/info', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url})
                });
                const data = await res.json();
                if (!data.success) throw new Error(data.error);
                let html = '<div class="video-info">';
                html += '<img src="' + data.thumbnail + '" class="thumbnail"/>';
                html += '<h3>' + data.title + '</h3>';
                html += '<p>By: ' + data.author + '</p>';
                html += '<h4>Download:</h4>';
                data.streams.forEach(s => {
                    html += '<button class="stream-btn" onclick="download(' + s.itag + ', \'' + s.type + '\')">';
                    html += '<span>' + s.quality + ' (' + s.size + ')</span><span>⬇️</span></button>';
                });
                html += '</div>';
                document.getElementById('result').innerHTML = html;
            } catch (e) {
                document.getElementById('result').innerHTML = '<div class="error">Error: ' + e.message + '</div>';
            } finally {
                document.getElementById('loading').style.display = 'none';
            }
        }
        function download(itag, type) {
            const url = document.getElementById('url').value;
            window.location.href = '/api/download?url=' + encodeURIComponent(url) + '&itag=' + itag + '&type=' + type;
        }
    </script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/info', methods=['POST'])
def get_info():
    try:
        data = request.get_json()
        url = data.get('url')
        if not url:
            return jsonify({'error': 'URL required'}), 400
        yt = YouTube(url, use_oauth=False, allow_oauth_cache=True)
        streams = []
        for s in yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc():
            size = f"{s.filesize // (1024*1024)}MB" if s.filesize else "Unknown"
            streams.append({'itag': s.itag, 'quality': s.resolution, 'size': size, 'type': 'video'})
        audio = yt.streams.get_audio_only()
        if audio:
            size = f"{audio.filesize // (1024*1024)}MB" if audio.filesize else "Unknown"
            streams.append({'itag': 'audio', 'quality': 'Audio Only', 'size': size, 'type': 'audio'})
        return jsonify({
            'success': True,
            'title': yt.title,
            'author': yt.author,
            'thumbnail': yt.thumbnail_url,
            'streams': streams
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/download', methods=['GET'])
def download():
    try:
        url = request.args.get('url')
        itag = request.args.get('itag')
        dtype = request.args.get('type', 'video')
        yt = YouTube(url, use_oauth=False, allow_oauth_cache=True)
        temp_dir = tempfile.gettempdir()
        if dtype == 'audio' or itag == 'audio':
            stream = yt.streams.get_audio_only()
            file_path = os.path.join(temp_dir, f"{yt.video_id}.mp3")
            stream.download(output_path=temp_dir, filename=f"{yt.video_id}.mp3")
            return send_file(file_path, as_attachment=True, download_name=f"{yt.title}.mp3")
        else:
            stream = yt.streams.get_by_itag(int(itag))
            file_path = os.path.join(temp_dir, f"{yt.video_id}.mp4")
            stream.download(output_path=temp_dir, filename=f"{yt.video_id}.mp4")
            return send_file(file_path, as_attachment=True, download_name=f"{yt.title}.mp4")
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)