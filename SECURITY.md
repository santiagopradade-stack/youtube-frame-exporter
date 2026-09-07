# Seguridad de distribución

## Modelo de publicación

1. Compilar siempre desde este código fuente con `build.ps1`.
2. Revisar que las seis pruebas terminen correctamente.
3. Firmar el ejecutable final con un certificado RSA de firma de código confiable.
4. Verificar la firma con `verify-signature.ps1` antes de distribuirlo.
5. Publicar también el hash SHA-256 mostrado por `build.ps1`.

## Certificados

- No guardes certificados, claves privadas ni contraseñas en este proyecto.
- Mantén el certificado en el almacén seguro de Windows o usa Microsoft Trusted Signing.
- El texto `CompanyName = Studio Moka` no prueba la identidad del publicador; Authenticode sí.

## Control inteligente de aplicaciones

Windows puede bloquear cualquier compilación nueva sin firma, incluso si el código es legítimo. No se debe desactivar la protección para distribuir o probar una versión. La solución de publicación es firmar todos los binarios entregados con un certificado compatible y confiable.

