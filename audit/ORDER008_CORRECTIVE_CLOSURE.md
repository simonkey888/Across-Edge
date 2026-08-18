# ORDER-008 — cierre correctivo posterior al checkpoint AUD 5288891689

## Fuente y autoridad

- Orden activa: `ORDER-008` / Issue #7.
- Corrective checkpoint: comentario `5288891689`.
- Fuente corregida: `157a21f82c7172dea267b239a8accb7fd289ed06`.
- Rama: `order-001-shadow-relayer`.
- PR: #2, Draft, sin merge.
- `main`: `044d195f134178b6127af5dd3f5ad7d660d32e54`, sin cambios.
- Upstream pin: `741ca9f7d72923f7b13c1c2462ca90eba81e1a87`, sin cambios.
- Patch SHA-256 registrado: `8cf71677303d75a178f5a9a79c0a3127935afcf753623668b55a5535fe25ce19`.

## Correcciones de causa raíz aplicadas

1. T0 repetido con fingerprint idéntico y sin etapas downstream refresca el intento existente sin reemplazar el primer T0 ni su identidad.
2. Las observaciones de fills quedan estrictamente acotadas por `run_id`; duplicados activos conservan la primera observación y replay post-reorg puede registrar una nueva observación del mismo evento para ese run.
3. El rewind run-local restaura estado candidato, tiempo de decisión, historial de transiciones y ganador desde evidencia superviviente.
4. El orden de rewind conserva primero las claves condenadas y desactiva la membresía del run antes de limpiar snapshots/derivados.
5. El rewind global invalida fills removidos para los runs y reconstruye ganadores usando únicamente fills activos del run correspondiente.
6. El fixture `make_deposit` admite `recipient` y `output_amount` sin alterar defaults.
7. La prueba de equivalencia reorg usa `observed_wall_utc` explícito para eliminar no determinismo de reloj.
8. Los cuatro headers de hunks indicados por AUD fueron corregidos y el manifest conserva el upstream SHA mientras actualiza sólo el hash del patch.

## Verificación estática remota

Se contrastaron los contextos del patch con los archivos del upstream exactamente pinneado mediante GitHub y no se cambió el SHA upstream. Esto no se reporta como sustituto de `git apply --check` ni de build/runtime.

## Nuevo bloqueo concreto de ejecución

Después de las correcciones, la superficie GitHub conectada no permite iniciar el rerun requerido en Codespaces:

- listado de Codespaces del usuario accesible: `total_count=0`;
- endpoint de Codespaces del repositorio: `HTTP 403 Resource not accessible by integration`;
- no existe una operación create/start Codespace expuesta por la integración disponible;
- GitHub Actions tampoco constituye fallback: run `31767779182`, job `94667091496`, HEAD `157a21f...`, `steps=[]`, sin runner asignado, bloqueado por restricción de billing/spending-limit antes de ejecutar software.

Por lo tanto no existe evidencia fresca post-corrección de pytest, compileall, secret scan, safety runtime, apply/build upstream, red o shadow. No se reutiliza ningún PASS histórico y no se declara fallo de software del HEAD corregido.

## Seguridad

`AUTHORIZED_SPEND_USD=0`, `PRIVATE_KEYS=0`, `SIGNING=0`, `TRANSACTIONS=0`, `WRITE_RPC=0`, `ONCHAIN_VALUE_TRANSFER=0`, `LIVE_FINANCIAL_EXECUTION=0`, `MERGE=NO`, `MAIN_UNCHANGED=YES`.

## Clasificación

`STATUS=BLOCKED_AFTER_CORRECTIVE_SOURCE`.

La siguiente acción válida requiere un entorno Codespaces realmente ejecutable sobre `order-001-shadow-relayer` y un rerun completo desde el HEAD corregido; no corresponde fabricar PASS ni avanzar a network/shadow sin esos gates.
