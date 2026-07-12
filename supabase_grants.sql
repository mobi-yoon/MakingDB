-- 테이블 접근 권한 부여 (RLS 정책은 이 권한이 있어야 적용됨)

grant select on public.recipes, public.scrolls, public.materials to anon, authenticated;
grant insert, update, delete on public.recipes, public.scrolls, public.materials to authenticated;
