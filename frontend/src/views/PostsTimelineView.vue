<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import service from '../api'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'

const route=useRoute(),router=useRouter()
const simId=computed(()=>route.params.simulationId)
const carregando=ref(true),erro=ref(''),allPosts=ref([]),filtro=ref('todos'),busca=ref('')
const cores=['#00e5c3','#7c6ff7','#1da1f2','#f5a623','#ff5a5a','#e91e9c','#4caf50','#ff9800','#9c27b0','#00bcd4']
function ini(n){return(n||'??').split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase()}
function cor(n){let h=0;for(let i=0;i<(n||'').length;i++)h=n.charCodeAt(i)+((h<<5)-h);return cores[Math.abs(h)%cores.length]}
function sent(p){const l=p.num_likes||0,d=p.num_dislikes||0;if(l>d*2)return'pos';if(d>l)return'neg';return'neu'}

onMounted(async()=>{
  carregando.value=true
  try{
    const[twR,rdR]=await Promise.all([
      service.get(`/api/simulation/${simId.value}/posts`,{params:{platform:'twitter',limit:200}}),
      service.get(`/api/simulation/${simId.value}/posts`,{params:{platform:'reddit',limit:200}})
    ])
    const tw=(twR?.data?.data?.posts||twR?.data?.posts||[]).map(p=>({...p,platform:'twitter'}))
    const rd=(rdR?.data?.data?.posts||rdR?.data?.posts||[]).map(p=>({...p,platform:'reddit'}))
    allPosts.value=[...tw,...rd].sort((a,b)=>new Date(b.created_at||0)-new Date(a.created_at||0))
  }catch(e){erro.value=e?.message||'Erro'}finally{carregando.value=false}
})

const filtered=computed(()=>{
  let r=allPosts.value
  if(filtro.value==='twitter')r=r.filter(p=>p.platform==='twitter')
  if(filtro.value==='reddit')r=r.filter(p=>p.platform==='reddit')
  if(filtro.value==='positivo')r=r.filter(p=>sent(p)==='pos')
  if(filtro.value==='negativo')r=r.filter(p=>sent(p)==='neg')
  if(busca.value.trim()){const q=busca.value.toLowerCase();r=r.filter(p=>(p.content||p.text||'').toLowerCase().includes(q)||(p.author||p.username||'').toLowerCase().includes(q))}
  return r
})
const totalTw=computed(()=>allPosts.value.filter(p=>p.platform==='twitter').length)
const totalRd=computed(()=>allPosts.value.filter(p=>p.platform==='reddit').length)
const totalPos=computed(()=>allPosts.value.filter(p=>sent(p)==='pos').length)
const totalNeg=computed(()=>allPosts.value.filter(p=>sent(p)==='neg').length)
</script>
<template>
  <AppShell title="Timeline de Posts">
    <template #actions>
      <AugurButton variant="ghost" @click="router.push(`/simulacao/${simId}/agentes`)">🧠 Agentes</AugurButton>
      <AugurButton variant="ghost" @click="router.back()">← Voltar</AugurButton>
    </template>
    <div v-if="carregando" class="st"><div class="spin"></div>Carregando posts...</div>
    <div v-else-if="erro" class="st err">⚠️ {{erro}}</div>
    <div v-else>
      <div class="sb"><div class="ss"><span class="sv">{{allPosts.length}}</span><span class="sl">Total</span></div><div class="ss"><span class="sv" style="color:#1da1f2">{{totalTw}}</span><span class="sl">Twitter</span></div><div class="ss"><span class="sv" style="color:#ff4500">{{totalRd}}</span><span class="sl">Reddit</span></div><div class="ss"><span class="sv" style="color:#00e5c3">{{totalPos}}</span><span class="sl">Positivos</span></div><div class="ss"><span class="sv" style="color:#ff5a5a">{{totalNeg}}</span><span class="sl">Negativos</span></div></div>
      <div class="fb"><div class="fs"><button v-for="f in [{v:'todos',l:'Todos'},{v:'twitter',l:'🐦 Twitter'},{v:'reddit',l:'🔴 Reddit'},{v:'positivo',l:'😊 Positivos'},{v:'negativo',l:'😠 Negativos'}]" :key="f.v" :class="['ft',{ac:filtro===f.v}]" @click="filtro=f.v">{{f.l}}</button></div><input v-model="busca" placeholder="Buscar no conteúdo..." class="bx"/></div>
      <div class="tl">
        <div v-for="(p,i) in filtered" :key="i" class="tp">
          <div class="line"></div><div class="dot" :class="'d-'+sent(p)"></div>
          <div class="card">
            <div class="ch"><div class="ca" :style="{background:cor(p.author||p.username||p.user_name)}">{{ini(p.author||p.username||p.user_name)}}</div><div class="cm"><div class="cn">{{p.author||p.username||p.user_name||'Agente'}}</div><div class="ci"><span class="cp">{{p.platform==='twitter'?'🐦':'🔴'}} {{p.platform}}</span><span class="ct" v-if="p.created_at">{{new Date(p.created_at).toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})}}</span></div></div></div>
            <div class="cb">{{p.content||p.text||'Sem conteúdo.'}}</div>
            <div class="cx"><span style="color:#ff5a5a">❤️ {{p.num_likes||0}}</span><span v-if="p.num_dislikes">👎 {{p.num_dislikes}}</span><span v-if="p.num_comments">💬 {{p.num_comments}}</span></div>
          </div>
        </div>
        <div v-if="!filtered.length" class="empty">Nenhum post encontrado.</div>
      </div>
    </div>
  </AppShell>
</template>
<style scoped>
.st{display:flex;flex-direction:column;align-items:center;gap:14px;padding:60px;color:var(--text-muted)}.err{color:var(--danger)}
.spin{width:24px;height:24px;border:3px solid var(--border-md);border-top-color:var(--accent);border-radius:50%;animation:sp .7s linear infinite}@keyframes sp{to{transform:rotate(360deg)}}
.sb{display:flex;gap:12px;margin-bottom:14px}.ss{background:var(--bg-surface);border:1px solid var(--border);border-radius:10px;padding:12px 18px;text-align:center;flex:1}.sv{font-size:20px;font-weight:800;font-family:monospace;display:block}.sl{font-size:10px;color:var(--text-muted);text-transform:uppercase;margin-top:2px}
.fb{display:flex;gap:12px;align-items:center;margin-bottom:16px}.fs{display:flex;gap:4px;flex:1}.ft{background:none;border:1px solid var(--border);color:var(--text-muted);padding:6px 12px;border-radius:8px;font-size:11px;cursor:pointer;transition:all .15s}.ft.ac{background:var(--accent2);color:#fff;border-color:var(--accent2)}.ft:hover:not(.ac){border-color:var(--accent2);color:var(--accent2)}
.bx{background:var(--bg-surface);border:1px solid var(--border);color:var(--text-primary);padding:7px 12px;border-radius:8px;font-size:12px;outline:none;width:200px}.bx:focus{border-color:var(--accent2)}
.tl{position:relative;padding-left:24px}
.tp{position:relative;margin-bottom:12px;display:flex}.line{position:absolute;left:7px;top:0;bottom:-12px;width:2px;background:var(--border)}.dot{position:absolute;left:2px;top:16px;width:12px;height:12px;border-radius:50%;border:2px solid var(--bg-base);z-index:1}.d-pos{background:#00e5c3}.d-neg{background:#ff5a5a}.d-neu{background:var(--text-muted)}
.card{margin-left:20px;background:var(--bg-surface);border:1px solid var(--border);border-radius:12px;padding:14px 16px;flex:1;display:flex;flex-direction:column;gap:8px}
.ch{display:flex;align-items:center;gap:10px}.ca{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;color:#fff;flex-shrink:0}.cn{font-size:13px;font-weight:700;color:var(--text-primary)}.ci{display:flex;gap:8px;font-size:10px;color:var(--text-muted)}.cp{font-weight:600}
.cb{font-size:13px;color:var(--text-secondary);line-height:1.7}.cx{display:flex;gap:12px;font-size:11px;color:var(--text-muted)}
.empty{text-align:center;padding:32px;color:var(--text-muted)}
@media(max-width:680px){.sb{flex-wrap:wrap}.fb{flex-direction:column}.bx{width:100%}}
</style>
