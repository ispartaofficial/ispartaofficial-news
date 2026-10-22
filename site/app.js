'use strict';
fetch('data.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json()}).then(data=>{
 const status=document.getElementById('status');
 status.textContent=`Son hazırlık: ${new Date(data.generated_at).toLocaleString('tr-TR')} · Otomatik paylaşım: ${data.publishing_enabled?'etkin':'kapalı'}`;
 for(const post of data.posts){
  const path=post.assets?.feed?.[0];
  if(!path||!/^media\/[a-f0-9]{24}\/feed-[1-9][0-9]?\.jpg$/.test(path))continue;
  const article=document.createElement('article'),image=document.createElement('img'),caption=document.createElement('p');
  image.src=path;image.alt=post.title;image.loading='lazy';caption.textContent=`${post.title} · ${post.status}`;
  article.append(image,caption);document.getElementById('cards').append(article);
 }
 for(const source of data.source_health){const li=document.createElement('li');li.textContent=`${source.source_id}: ${source.status} · ${source.parsed} kayıt`;document.getElementById('sources').append(li)}
}).catch(()=>{document.getElementById('status').textContent='Son araştırma şu anda yüklenemiyor.'});
