import urllib.request
import re

M3U_URL = "https://iptv-org.github.io/iptv/countries/ar.m3u"
OUTPUT_FILE = "ar_hd.m3u"

CATEGORY_MAP = {
    "News": "Noticias",
    "Sports": "Deportes",
    "Entertainment": "Entretenimiento",
    "Animation;Kids": "Kids",
    "Animation;Classic;Entertainment": "Kids",
    "Animation": "Kids",
    "Kids": "Kids",
    "Music": "Música",
    "Movies": "Cine y Series",
    "Series": "Cine y Series",
    "Classic;Movies": "Cine y Series",
    "Culture;Documentary;Entertainment;General;Movies;Music": "Cultura y Documentales",
    "Culture;News": "Noticias",
    "Culture": "Cultura y Documentales",
    "General": "General",
    "Education": "Educación",
    "Religious": "Religión",
    "Business;News": "Noticias",
    "Outdoor": "Agro",
    "Undefined": "Otros"
}

def map_category(group_title):
    # Si viene vacío o no está mapeado
    if not group_title:
        return "Otros"
    
    # Intenta mapear directo
    if group_title in CATEGORY_MAP:
        return CATEGORY_MAP[group_title]
    
    # Si tiene varias categorías (separadas por ;) vemos la primera
    first_cat = group_title.split(';')[0]
    if first_cat in CATEGORY_MAP:
        return CATEGORY_MAP[first_cat]
        
    return "Otros"

def is_hd(name, tvg_id):
    # Consideramos 720p, 1080p, 2160p o etiquetas HD en el nombre o id
    name_lower = name.lower()
    id_lower = tvg_id.lower()
    if '720p' in name_lower or '1080p' in name_lower or '2160p' in name_lower:
        return True
    if '@hd' in id_lower or ' hd' in name_lower or '(hd)' in name_lower:
        return True
    return False

def download_m3u(url):
    print(f"Descargando lista de {url}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Error descargando la lista {url}: {e}")
        return ""

def process_channel_block(current_extinf, current_opts, url_line, is_intl_music=False):
    match_group = re.search(r'group-title="(.*?)"', current_extinf)
    match_tvg_id = re.search(r'tvg-id="(.*?)"', current_extinf)
    
    group_title = match_group.group(1) if match_group else ""
    tvg_id = match_tvg_id.group(1) if match_tvg_id else ""
    name = current_extinf.split(',')[-1].strip()
    
    if is_intl_music:
        name_lower = name.lower()
        cat_lower = group_title.lower()
        id_lower = tvg_id.lower()
        
        # Filtro estricto de resolución 1080p o 2160p
        if '1080p' not in name_lower and '2160p' not in name_lower and '1080p' not in id_lower and '2160p' not in id_lower:
            return None
            
        # Exclusiones explícitas
        if 'hip-hop' in name_lower or 'hip hop' in name_lower or 'radio' in name_lower or 'hip-hop' in cat_lower or 'radio' in cat_lower:
            return None
            
        # Marcas y géneros prioritarios
        brands = ['mtv', 'vevo', 'billboard', 'xite', 'now']
        genres = ['rock', 'indie', 'pop', 'hits', 'r&b', 'alternative', 'classic', 'éxitos', 'exitos']
        
        has_brand = any(b in name_lower or b in id_lower for b in brands)
        has_genre = any(g in name_lower or g in cat_lower for g in genres)
        is_music_cat = 'music' in cat_lower
        
        if not (has_brand or has_genre or is_music_cat):
            return None
            
        # Asignar a la categoría Música
        cat_es = "Música"
    else:
        # Lógica original para canales de Argentina
        if not is_hd(name, tvg_id):
            return None
        cat_es = map_category(group_title)

    # Reemplazamos el group-title original por la categoría en español
    if match_group:
        new_extinf = current_extinf.replace(f'group-title="{group_title}"', f'group-title="{cat_es}"')
    else:
        # Si no tenía group-title, se lo agregamos
        new_extinf = current_extinf.replace(',', f' group-title="{cat_es}",', 1)
    return {
        'category': cat_es,
        'name': name,
        'extinf': new_extinf,
        'opts': current_opts,
        'url': url_line
    }

def parse_m3u_content(content, is_intl_music=False):
    lines = content.splitlines()
    channels = []
    current_extinf = None
    current_opts = []
    
    for line in lines:
        if line.startswith("#EXTINF:"):
            current_extinf = line
        elif line.startswith("#EXTVLCOPT:"):
            current_opts.append(line)
        elif line.startswith("http") and current_extinf:
            ch_data = process_channel_block(current_extinf, current_opts, line, is_intl_music)
            if ch_data:
                channels.append(ch_data)
            current_extinf = None
            current_opts = []
        elif not line.startswith("#") and line.strip():
            current_extinf = None
            current_opts = []
            
    return channels

def generate_playlist():
    all_channels = []
    
    # 1. Procesar Argentina
    content_ar = download_m3u(M3U_URL)
    if content_ar:
        ar_channels = parse_m3u_content(content_ar, is_intl_music=False)
        all_channels.extend(ar_channels)
        
    # 2. Procesar Música Internacional
    INTL_URLS = [
        "https://iptv-org.github.io/iptv/countries/us.m3u",
        "https://iptv-org.github.io/iptv/countries/uk.m3u"
    ]
    for url in INTL_URLS:
        content_intl = download_m3u(url)
        if content_intl:
            intl_channels = parse_m3u_content(content_intl, is_intl_music=True)
            all_channels.extend(intl_channels)
            
    # Añadir TV Pública manualmente
    all_channels.append({
        'category': 'General',
        'name': 'TV Pública HD',
        'extinf': '#EXTINF:-1 tvg-id="TVPublica.ar" http-referrer="https://www.tvpublica.com.ar/" group-title="General" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/4/4b/Televisi%C3%B3n_P%C3%BAblica_Argentina_logo.png", TV Pública HD',
        'opts': ['#EXTVLCOPT:http-referrer=https://www.tvpublica.com.ar/'],
        'url': 'https://edgetvp.global.ssl.fastly.net/b16/ngrp:c7_vivo01_dai_source-20001_all/playlist.m3u8'
    })

    # Filtrar posibles duplicados exactos (por nombre y url)
    unique_channels = []
    seen = set()
    for ch in all_channels:
        identifier = f"{ch['name']}-{ch['url']}"
        if identifier not in seen:
            seen.add(identifier)
            unique_channels.append(ch)

    # Ordenar por categoría (alfabéticamente) y luego por nombre del canal
    unique_channels.sort(key=lambda x: (x['category'], x['name']))

    print(f"Escribiendo {len(unique_channels)} canales HD en {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        current_cat = None
        for ch in unique_channels:
            if ch['category'] != current_cat:
                current_cat = ch['category']
                f.write(f"\n# {'=' * 60}\n")
                f.write(f"# GRUPO: {current_cat.upper()}\n")
                f.write(f"# {'=' * 60}\n\n")
                
            f.write(ch['extinf'] + "\n")
            for opt in ch['opts']:
                f.write(opt + "\n")
            f.write(ch['url'] + "\n")
            
    print("¡Lista generada con éxito!")

if __name__ == "__main__":
    generate_playlist()
