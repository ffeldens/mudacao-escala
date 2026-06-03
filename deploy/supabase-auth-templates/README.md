# Supabase Auth — Custom SMTP + Templates HTML

Configuração one-time pra que os emails de autenticação (magic link,
recovery, etc) saiam **pelo Resend** com o domínio `mudacao.com.br` e
o template HTML com brand MudAção (em vez do default genérico do Supabase).

## Por que trocar o SMTP do Supabase

- **Rate limit Supabase grátis**: ~3 emails/hora compartilhados com todo
  mundo. Em produção isso bloqueia logins.
- **Sender**: padrão é `noreply@mail.app.supabase.io` — sem brand MudAção,
  cai em spam com mais facilidade.
- **Template**: Supabase tem template inline básico — não combina com o
  resto dos emails transacionais.

Com Resend custom:
- DKIM + SPF do domínio `mudacao.com.br` (já configurados pros emails do
  Resend)
- Sender `noreply@mudacao.com.br` consistente com os transacionais
- Template HTML 100% controlado por mim

## Como configurar (Supabase Dashboard)

### 1. SMTP custom

Em **Project Settings → Authentication → SMTP Settings**, marcar
"**Enable custom SMTP**" e preencher:

| Campo | Valor |
|---|---|
| Sender email | `noreply@mudacao.com.br` *(ver nota abaixo)* |
| Sender name | `MudAção Escala` |
| Host | `smtp.resend.com` |
| Port number | `465` |
| Username | `resend` |
| Password | API key do Resend (`re_...`) — a mesma do `.env` |
| Minimum interval | `60` (segundos entre emails pro mesmo user) |

> **Sender email — escolha**: qualquer endereço no domínio verificado vale.
> Recomendo `noreply@mudacao.com.br` pra auth (semântica de "não responda
> a este email"), distinto do `simulador@mudacao.com.br` que os emails
> transacionais usam (esse a pessoa PODE responder, cai em Felipe via
> reply-to). Se preferir manter um único sender, usa o mesmo
> `simulador@mudacao.com.br` em todo lugar — funciona idêntico.

> **Importante**: o domínio `mudacao.com.br` precisa estar verificado no
> Resend (Domains → Verify). Sem isso, o Resend rejeita o envio.

Clica **Save**.

### 2. Templates HTML

Em **Authentication → Email Templates**, troca cada template pelos HTMLs
nesta pasta:

| Tipo de email | Arquivo nesta pasta | Variável obrigatória |
|---|---|---|
| **Magic Link** | `magic-link.html` | `{{ .ConfirmationURL }}` |
| **Confirm signup** | `confirmation.html` | `{{ .ConfirmationURL }}` |
| **Reset Password** | `recovery.html` | `{{ .ConfirmationURL }}` |
| **Change Email Address** | `email-change.html` | `{{ .ConfirmationURL }}`, `{{ .Email }}`, `{{ .NewEmail }}` |
| **Invite user** | `invite.html` | `{{ .ConfirmationURL }}` |

Em cada um:
1. Cola o HTML inteiro no campo "Message (HTML)"
2. Ajusta o "Subject" (sugestões abaixo)
3. Save

### Subjects sugeridos

| Template | Subject |
|---|---|
| Magic Link | `Seu link de acesso ao MudAção Escala` |
| Confirm signup | `Confirme seu email — MudAção Escala` |
| Reset Password | `Redefina sua senha — MudAção Escala` |
| Change Email | `Confirme a troca de email — MudAção Escala` |
| Invite | `Você foi convidado pro MudAção Escala` |

## Variáveis disponíveis no template

Supabase expõe estas variáveis via Go template syntax (`{{ .X }}`):

| Variável | O que é |
|---|---|
| `{{ .ConfirmationURL }}` | Link clicável com token (1h validade) |
| `{{ .Email }}` | Email do destinatário (atual) |
| `{{ .NewEmail }}` | Novo email (só no template de change-email) |
| `{{ .Token }}` | Token bruto (6 dígitos) — pra OTP, não usar em link |
| `{{ .TokenHash }}` | Hash do token |
| `{{ .SiteURL }}` | URL do site (de Project Settings → Authentication) |
| `{{ .RedirectTo }}` | URL final após autenticação |
| `{{ .Data.NomeCustom }}` | Qualquer metadata custom passado no `signInWithOtp` |

> Os templates nesta pasta só usam `{{ .ConfirmationURL }}` (e `Email` /
> `NewEmail` no email-change). Mantenha simples — quanto menos lógica no
> template, menos coisa pode quebrar.

## Como validar

Depois de salvar, testa em uma janela anônima:

1. Acessa `https://simulaescala.mudacao.com.br/login`
2. Digita seu email → clica em "Enviar magic link"
3. Vai pra inbox e confira:
   - ✅ Remetente é `noreply@mudacao.com.br` (não `noreply@mail.app.supabase.io`)
   - ✅ Subject é o customizado (não o default Supabase)
   - ✅ Visual MudAção (gradient verde no header, botão verde escuro)
   - ✅ DKIM passa (no Gmail: clica em "show original" → procurar `dkim=pass`)
4. Clica no botão → entra na conta normalmente

## Como atualizar os templates depois

Os arquivos HTML aqui são a fonte da verdade. Se mudar um template:

1. Edita o `.html` neste diretório
2. Commit + push no Git
3. **Copia o conteúdo atualizado** e cola no Supabase Dashboard (não
   tem como sincronizar automático — o Supabase não tem API pública pra
   templates)
4. Save

## Troubleshooting

### Email não chega após habilitar custom SMTP

- API key do Resend errada / expirada → trocar e testar novamente.
- Domínio `mudacao.com.br` não verificado no Resend → ir em Resend →
  Domains e seguir o wizard de DNS (TXT + DKIM).
- Spam filter agressivo → procurar em spam/lixeira primeiro.
- Logs do Resend: https://resend.com/emails — vê se o envio aparece lá.

### "Email rate limit exceeded"

- Configura "Minimum interval" maior em SMTP Settings (60s já é seguro).
- Resend free dá 100 emails/dia — pra mais, ativar plano pago.

### Template HTML quebrado / não renderiza

- Variáveis precisam ser `{{ .ConfirmationURL }}` (com espaços e ponto).
- Tags HTML auto-fechantes (`<br/>`) podem quebrar Go template — usa
  `<br>` simples.
- Testa primeiro em um inbox real (Gmail/Outlook) — Mailtrap/MailHog
  podem mascarar problemas reais.
