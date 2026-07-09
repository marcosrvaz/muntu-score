-- Banco curado learn-from-ads (plano-mestre 2026-07-09, decisões D1-D5, D8).
-- Tabela ÚNICA multi-tipo: filtro SQL barato antes do blend vetorial.
create extension if not exists vector;

create table if not exists assets (
  id          uuid primary key default gen_random_uuid(),
  asset_type  text not null check (asset_type in ('music', 'sfx', 'vo')),
  source      text not null check (source in ('own', 'artlist', 'epidemic')),
  pointer     text not null,   -- path local (own/artlist) ou 'epidemic:<track_id>' (ponteiro)
  titulo      text not null default '',
  era         text not null default '',
  bpm         int,
  license_ok  boolean not null default false,
  tags        jsonb not null default '{}'::jsonb,   -- tags completas (muntu/tags.py)
  descritor   text not null,                        -- tags.descritor() -> input do text_emb
  text_emb    vector(1536),    -- text-embedding-3-small via OpenRouter (D4): intenção.
                               -- Cobre TODOS incl. epidemic-ponteiro
  audio_emb   vector(512),     -- CLAP larger_clap_music (D3): som. NULL p/ epidemic (D8)
  created_at  timestamptz not null default now(),
  unique (source, pointer)
);

-- RRF em SQL puro (D1): rank-fusion evita normalizar distribuições incompatíveis
-- (cosine de espaços text vs audio). k=60 (Cormack 2009). Sem índice ANN (D2):
-- <10k rows -> seq scan exato, recall 100%.
create or replace function busca_hibrida(
  q_text        vector(1536),
  q_audio       vector(512) default null,
  tipo          text default 'music',
  filtro_era    text default null,
  so_licenciados boolean default false,
  k             int default 60,
  n             int default 10,
  peso_texto    float default 1.0,
  peso_audio    float default 1.0
) returns table (id uuid, pointer text, titulo text, descritor text, tags jsonb, rrf float)
language sql stable as $$
  with base as (
    select a.* from assets a
    where a.asset_type = tipo
      and (filtro_era is null or a.era = filtro_era)
      and (not so_licenciados or a.license_ok)
  ),
  rt as (
    select b.id, row_number() over (order by b.text_emb <=> q_text) as r
    from base b where b.text_emb is not null and q_text is not null
  ),
  ra as (
    select b.id, row_number() over (order by b.audio_emb <=> q_audio) as r
    from base b where b.audio_emb is not null and q_audio is not null
  )
  select b.id, b.pointer, b.titulo, b.descritor, b.tags,
         coalesce(peso_texto / (k + rt.r), 0) + coalesce(peso_audio / (k + ra.r), 0) as rrf
  from base b
  left join rt on rt.id = b.id
  left join ra on ra.id = b.id
  where rt.id is not null or ra.id is not null
  order by rrf desc, b.id
  limit n;
$$;
