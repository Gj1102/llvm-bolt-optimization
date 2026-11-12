import urllib.request, json, hashlib, tarfile, io, gzip, http.client
from pathlib import Path
opener = urllib.request.build_opener(urllib.request.ProxyHandler({'https': 'http://127.0.0.1:7897'}))
def get(url, headers={}):
    return opener.open(urllib.request.Request(url, headers=headers), timeout=120).read()
token = json.loads(get('https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/ubuntu:pull'))['token']
headers = {'Authorization':'Bearer '+token, 'Accept':'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.manifest.v1+json'}
base = 'https://registry-1.docker.io/v2/library/ubuntu/'
manifest = json.loads(get(base+'manifests/24.04', headers))
if 'manifests' in manifest:
    selected = next(x for x in manifest['manifests'] if x.get('platform',{}).get('architecture')=='amd64' and x['platform']['os']=='linux')
    manifest = json.loads(get(base+'manifests/'+selected['digest'], headers))
config = get(base+'blobs/'+manifest['config']['digest'], headers)
assert 'sha256:'+hashlib.sha256(config).hexdigest()==manifest['config']['digest']
out = Path('.ubuntu-base.tar')
with tarfile.open(out, 'w') as tar:
    def add(name, data):
        info=tarfile.TarInfo(name); info.size=len(data); tar.addfile(info,io.BytesIO(data))
    cname=manifest['config']['digest'].split(':')[1]+'.json'
    add(cname, config)
    layers=[]
    for i, layer in enumerate(manifest['layers']):
        cache=Path('.ubuntu-layer-'+str(i))
        data=cache.read_bytes() if cache.exists() else b''
        for attempt in range(100):
            if len(data)==layer['size']: break
            request_headers=dict(headers)
            request_headers['Range']=f'bytes={len(data)}-{min(len(data)+1048575,layer["size"]-1)}'
            response=opener.open(urllib.request.Request(base+'blobs/'+layer['digest'],headers=request_headers),timeout=120)
            if response.status==200: data=b''
            try: data+=response.read()
            except http.client.IncompleteRead as error: data+=error.partial
            cache.write_bytes(data)
            print('layer',i,len(data),'/',layer['size'],flush=True)
        assert 'sha256:'+hashlib.sha256(data).hexdigest()==layer['digest']
        name=f'layer{i}/layer.tar'; add(name,gzip.decompress(data)); layers.append(name)
    add('manifest.json', json.dumps([{'Config':cname,'RepoTags':['ubuntu:24.04'],'Layers':layers}]).encode())
Path('llvm-bolt-optimization/results/docker-base.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(out, out.stat().st_size)
