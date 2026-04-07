<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import service from '../api'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'

const route = useRoute(), router = useRouter()
const simId = computed(() => route.params.simulationId)
const agentIdx = computed(() => parseInt(route.params.agentId) || 0)
const carregando = ref(true), erro = ref(''), profile = ref(null), stats = ref(null), posts = ref([]), tab = ref('posts')
const cores = ['#00e5c3','#7c6ff7','#1da1f2','#f5a623','#ff5a5a','#e91e9c','#4caf50','#ff9800','#9c27b0','#00bcd4']
function iniciais(n){ return (n||'??').split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase() }
function corAvatar(n){ let h=0;for(let i=0;i<(n||'').length;i++)h=n.charCodeAt(i)+((h<<5)-h);return cores[Math.abs(h)%cores.length] }

onMounted(async()=>{
  carregando.value=true
  try{
    const pRes=await service.get(`/api/simulation/${simId.value}/profiles`)
    const all=(pRes?.data?.data||pRes?.data||{}).profiles||(pRes?.data?.data||pRes?.data)||[]
    profile.value=all[agentIdx.value]||all.find(p=>p.agent_id===agentIdx.value)||null
    try{ const sRes=await service.get(`/api/simulation/${simId.value}/agent-stats`);const ss=sRes?.data?.data?.stats||sRes?.data?.stats||[];stats.value=ss.find(s=>s.agent_id===agentIdx.value)||ss[agentIdx.value]||null }catch{}
    try{
      const [twR,rdR]=await Promise.all([service.get(`/api/simulation/${simId.value}/posts`,{params:{platform:'twitter',limit:100}}),service.get(`/api/simulation/${simId.value}/posts`,{params:{platform:'reddit',limit:100}})])
      const tw=(twR?.data?.data?.posts||twR?.data?.posts||[]).map(p=>({...p,platform:'twitter'}))
      const rd=(rdR?.data?.data?.posts||rdR?.data?.posts||[]).map(p=>({...p,platform:'reddit'}))
      const nm=profile.value?.name||profile.value?.user_name||''
      posts.value=[...tw,...rd].filter(p=>(p.author||p.username||p.user_name||'')===nm||p.user_id===agentIdx.value).sort((a,b)=>new Date(b.created_at||0)-new Date(a.created_at||0))
    }catch{}
    if(!profile.value)erro.value='Perfil não encontrado.'
  }catch(e){erro.value=e?.message||'Erro'}finally{carregando.value=false}
})

const totalLikes=computed(()=>posts.value.reduce((a,p)=>a+(p.num_likes||0),0))
const totalDislikes=computed(()=>posts.value.reduce((a,p)=>a+(p.num_dislikes||0),0))
const sentimentScore=computed(()=>{ if(!totalLikes.value&&!totalDislikes.value)return 50;return Math.round(totalLikes.value/Math.max(totalLikes.value+totalDislikes.value,1)*100) })
const actionBreakdown=computed(()=>{
  if(!stats.value?.action_types)return[]
  const lb={CREATE_POST:'📝 Posts',LIKE_POST:'❤️ Curtidas',REPOST:'🔄 Reposts',CREATE_COMMENT:'💬 Comentários',FOLLOW:'👥 Seguiu',LIKE_COMMENT:'👍 Curtiu coment.'}
  return Object.entries(stats.value.action_types).map(([t,c])=>({type:t,label:lb[t]||t,count:c})).sort((a,b)=>b.count-a.count)
})
function sent(p){const l=p.num_likes||0,d=p.num_dislikes||0;if(l>d*2)return 'pos';if(d>l)return 'neg';return 'neu'}
</script>
<template>
  <AppShell :title="profile?.name||'Perfil do Agente'">
    <template #actions>
      <AugurButton @click="router.push(`/simulacao/${simId}/posts`)">📝 Posts</AugurButton>
      <AugurButton variant="ghost" @click="router.push(`/simulacao/${simId}/agentes`)">← Agentes</AugurButton>
    </template>
    <div v-if="carregando" class="st"><div class="spin"></div>Carregando...</div>
    <div v-else-if="erro" class="st err">⚠️ {{erro}}</div>
    <div v-else-if="profile" class="page">
      <div class="hdr">
        <div class="av" :style="{background:corAvatar(profile.name)}">{{iniciais(profile.name)}}</div>
        <div class="info"><div class="nm">{{profile.name||profile.user_name}}</div><div class="rl">{{profile.role||profile.bio?.slice(0,80)||'Agente simulado'}}</div><div class="ps" v-if="profile.personality">{{profile.personality}}</div></div>
        <div class="gauge">
          <svg viewBox="0 0 120 120" width="80" height="80">
            <circle cx="60" cy="60" r="50" fill="none" stroke="var(--border)" stroke-width="8"/>
            <circle cx="60" cy="60" r="50" fill="none" :stroke="sentimentScore>60?'#00e5c3':sentimentScore>40?'#f5a623':'#ff5a5a'" stroke-width="8" stroke-linecap="round" :stroke-dasharray="`${sentimentScore*3.14} 314`" transform="rotate(-90 60 60)"/>
            <text x="60" y="56" text-anchor="middle" fill="var(--text-primary)" font-size="22" font-weight="800">{{sentimentScore}}</text>
            <text x="60" y="74" text-anchor="middle" fill="var(--text-muted)" font-size="10">Sentimento</text>
          </svg>
        </div>
      </div>
      <div class="sr">
        <div class="sc"><div class="sv">{{stats?.total_actions||posts.length||'—'}}</div><div class="sl">Ações</div></div>
        <div class="sc"><div class="sv">{{posts.length}}</div><div class="sl">Posts</div></div>
        <div class="sc"><div class="sv" style="color:#00e5c3">{{totalLikes}}</div><div class="sl">Likes</div></div>
        <div class="sc"><div class="sv" style="color:#ff5a5a">{{totalDislikes}}</div><div class="sl">Dislikes</div></div>
        <div class="sc" v-if="stats?.twitter_actions"><div class="sv" style="color:#1da1f2">{{stats.twitter_actions}}</div><div class="sl">Twitter</div></div>
        <div class="sc" v-if="stats?.reddit_actions"><div class="sv" style="color:#ff4500">{{stats.reddit_actions}}</div><div class="sl">Reddit</div></div>
      </div>
      <div class="bx" v-if="actionBreakdown.length">
        <div class="bxl">Tipos de Ação</div>
        <div class="abs"><div v-for="a in actionBreakdown" :key="a.type" class="abr"><span class="abl">{{a.label}}</span><div class="abt"><div class="abf" :style="{width:(a.count/(stats?.total_actions||1)*100)+'%'}"></div></div><span class="abc">{{a.count}}</span></div></div>
      </div>
      <div class="tabs"><button :class="['tb',{ac:tab==='posts'}]" @click="tab='posts'">📝 Posts ({{posts.length}})</button><button :class="['tb',{ac:tab==='bio'}]" @click="tab='bio'">🧠 Perfil</button></div>
      <div v-if="tab==='posts'" class="pl">
        <div v-for="(p,i) in posts" :key="i" class="pc" :class="'pc-'+sent(p)">
          <div class="ph"><span class="pp">{{p.platform==='twitter'?'🐦':'🔴'}} {{p.platform}}</span><span class="pt" v-if="p.created_at">{{new Date(p.created_at).toLocaleString('pt-BR')}}</span></div>
          <div class="pb">{{p.content||p.text||'Sem conteúdo.'}}</div>
          <div class="px"><span style="color:#ff5a5a">❤️ {{p.num_likes||0}}</span><span v-if="p.num_dislikes">👎 {{p.num_dislikes}}</span><span v-if="p.num_comments">💬 {{p.num_comments}}</span></div>
        </div>
        <div v-if="!posts.length" class="empty">Nenhum post deste agente.</div>
      </div>
      <div v-if="tab==='bio'" class="bio">
        <div v-for="[k,v] in Object.entries({Nome:profile.name,Username:profile.user_name,Papel:profile.role,Bio:profile.bio,Personalidade:profile.personality,Seguidores:profile.num_followers,Seguindo:profile.num_followings}).filter(([,v])=>v)" :key="k" class="bi"><span class="bk">{{k}}</span><span class="bv">{{v}}</span></div>
      </div>
    </div>
  </AppShell>
</template>
<style scoped>
.st{display:flex;flex-direction:column;align-items:center;gap:14px;padding:60px;color:var(--text-muted)}.err{color:var(--danger)}
.spin{width:24px;height:24px;border:3px solid var(--border-md);border-top-color:var(--accent);border-radius:50%;animation:sp .7s linear infinite}@keyframes sp{to{transform:rotate(360deg)}}
.page{display:flex;flex-direction:column;gap:16px}
.hdr{display:flex;align-items:center;gap:20px;background:var(--bg-surface);border:1px solid var(--border);border-radius:16px;padding:24px}
.av{width:72px;height:72px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:24px;font-weight:800;color:#fff;flex-shrink:0}
.info{flex:1}.nm{font-size:20px;font-weight:800;color:var(--text-primary)}.rl{font-size:13px;color:var(--accent2);margin-top:4px}.ps{font-size:12px;color:var(--text-muted);margin-top:6px;line-height:1.6;font-style:italic}
.sr{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}
.sc{background:var(--bg-surface);border:1px solid var(--border);border-radius:12px;padding:14px;text-align:center}
.sv{font-size:22px;font-weight:800;color:var(--text-primary);font-family:monospace}.sl{font-size:10px;color:var(--text-muted);text-transform:uppercase;margin-top:4px}
.bx{background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;padding:20px}.bxl{font-size:11px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:14px}
.abs{display:flex;flex-direction:column;gap:8px}.abr{display:flex;align-items:center;gap:10px}.abl{font-size:12px;color:var(--text-secondary);min-width:130px}.abt{flex:1;height:8px;background:var(--bg-overlay);border-radius:4px;overflow:hidden}.abf{height:100%;background:var(--accent2);border-radius:4px;transition:width .6s}.abc{font-size:12px;font-weight:700;font-family:monospace;min-width:30px;text-align:right}
.tabs{display:flex;gap:4px;background:var(--bg-surface);border:1px solid var(--border);border-radius:10px;padding:4px}.tb{flex:1;background:none;border:none;color:var(--text-muted);padding:8px;border-radius:8px;font-size:13px;cursor:pointer;font-weight:600}.tb.ac{background:var(--accent2);color:#fff}
.pl{display:flex;flex-direction:column;gap:8px}.pc{background:var(--bg-surface);border:1px solid var(--border);border-radius:12px;padding:16px;border-left:3px solid transparent}.pc-pos{border-left-color:#00e5c3}.pc-neg{border-left-color:#ff5a5a}.pc-neu{border-left-color:var(--border)}
.ph{display:flex;justify-content:space-between;margin-bottom:8px}.pp{font-size:11px;font-weight:600;color:var(--text-muted)}.pt{font-size:10px;color:var(--text-muted)}.pb{font-size:13px;color:var(--text-secondary);line-height:1.7}.px{display:flex;gap:12px;font-size:11px;margin-top:8px;color:var(--text-muted)}
.empty{text-align:center;padding:32px;color:var(--text-muted)}
.bio{display:flex;flex-direction:column;gap:2px}.bi{display:flex;padding:12px 16px;border-radius:8px;gap:16px}.bi:hover{background:var(--bg-raised)}.bk{font-size:12px;font-weight:700;color:var(--text-muted);min-width:120px;text-transform:uppercase}.bv{font-size:13px;color:var(--text-primary);line-height:1.6}
@media(max-width:1080px){.sr{grid-template-columns:repeat(3,1fr)}}@media(max-width:680px){.sr{grid-template-columns:repeat(2,1fr)}.hdr{flex-direction:column;text-align:center}}
</style>
