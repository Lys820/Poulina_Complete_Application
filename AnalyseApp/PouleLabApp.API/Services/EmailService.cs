using System.Net;
using System.Net.Mail;
using PouleLabApp.API.Services.Interfaces;

namespace PouleLabApp.API.Services
{
    // Implémentation du service d'envoi d'emails via System.Net.Mail
    // Utilise uniquement des bibliothèques intégrées à .NET — aucun package externe
    public class EmailService : IEmailService
    {
        private readonly IConfiguration _configuration;
        private readonly ILogger<EmailService> _logger;

        public EmailService(
            IConfiguration configuration,
            ILogger<EmailService> logger)
        {
            _configuration = configuration;
            _logger = logger;
        }

        // -------------------------------------------------------
        // Méthode principale d'envoi d'email
        // -------------------------------------------------------
        public async Task SendEmailAsync(
            string toEmail,
            string toName,
            string subject,
            string htmlBody)
        {
            try
            {
                var host     = _configuration["Email:Host"]!;
                var port     = int.Parse(_configuration["Email:Port"]!);
                var username = _configuration["Email:Username"]!;
                var password = _configuration["Email:Password"]!;
                var fromName = _configuration["Email:FromName"] ?? "PouleLabApp";

                using var client = new SmtpClient(host, port)
                {
                    Credentials = new NetworkCredential(username, password),
                    EnableSsl   = true
                };

                var message = new MailMessage
                {
                    From       = new MailAddress(username, fromName),
                    Subject    = subject,
                    Body       = htmlBody,
                    IsBodyHtml = true
                };

                message.To.Add(new MailAddress(toEmail, toName));

                await client.SendMailAsync(message);

                _logger.LogInformation(
                    "[Email] Email envoyé à {Email} — Sujet : {Subject}",
                    toEmail, subject);
            }
            catch (Exception ex)
            {
                // On log l'erreur sans bloquer le workflow
                _logger.LogError(ex,
                    "[Email] Échec d'envoi à {Email} — Sujet : {Subject}",
                    toEmail, subject);
            }
        }

        // -------------------------------------------------------
        // Templates d'emails
        // -------------------------------------------------------
        public async Task SendRequestSubmittedAsync(
            string toEmail, string toName, int requestId)
        {
            await SendEmailAsync(toEmail, toName,
                $"[PouleLabApp] Demande #{requestId} soumise avec succès",
                BuildTemplate(toName,
                    $"Votre demande d'analyse <strong>#{requestId}</strong> a été soumise avec succès.",
                    "Elle est maintenant en attente de réception par notre équipe.",
                    "#3B82F6"));
        }

        public async Task SendRequestReceivedAsync(
            string toEmail, string toName, int requestId)
        {
            await SendEmailAsync(toEmail, toName,
                $"[PouleLabApp] Demande #{requestId} réceptionnée",
                BuildTemplate(toName,
                    $"Votre demande d'analyse <strong>#{requestId}</strong> a été réceptionnée.",
                    "Elle sera assignée à un laborantin dans les plus brefs délais.",
                    "#8B5CF6"));
        }

        public async Task SendRequestAssignedAsync(
            string toEmail, string toName, int requestId)
        {
            await SendEmailAsync(toEmail, toName,
                $"[PouleLabApp] Demande #{requestId} assignée à un laborantin",
                BuildTemplate(toName,
                    $"Votre demande d'analyse <strong>#{requestId}</strong> a été assignée à un laborantin.",
                    "Les analyses sont en cours. Vous serez notifié dès que les résultats seront disponibles.",
                    "#F59E0B"));
        }

        public async Task SendResultsReadyAsync(
            string toEmail, string toName, int requestId)
        {
            await SendEmailAsync(toEmail, toName,
                $"[PouleLabApp] Résultats disponibles — Demande #{requestId}",
                BuildTemplate(toName,
                    $"Les résultats de votre demande d'analyse <strong>#{requestId}</strong> sont disponibles.",
                    "Connectez-vous à l'application pour consulter et télécharger votre bulletin d'analyses.",
                    "#10B981"));
        }

        public async Task SendRequestRejectedAsync(
            string toEmail, string toName, int requestId, string reason)
        {
            await SendEmailAsync(toEmail, toName,
                $"[PouleLabApp] Demande #{requestId} refusée",
                BuildTemplate(toName,
                    $"Votre demande d'analyse <strong>#{requestId}</strong> a été refusée.",
                    $"Raison : {reason}",
                    "#EF4444"));
        }

        public async Task SendDeadlineOverdueAsync(
            string toEmail, string toName, int requestId, string phase)
        {
            await SendEmailAsync(toEmail, toName,
                $"[PouleLabApp] ⚠️ Retard détecté — Demande #{requestId}",
                BuildTemplate(toName,
                    $"Un retard a été détecté sur la demande <strong>#{requestId}</strong>.",
                    $"La phase <strong>{phase}</strong> a dépassé son échéance prévue.",
                    "#F97316"));
        }

        // -------------------------------------------------------
        // Template HTML générique
        // -------------------------------------------------------
        private static string BuildTemplate(
            string name, string mainMessage,
            string subMessage, string accentColor) => $@"
            <!DOCTYPE html>
            <html>
            <body style='font-family:Arial,sans-serif;background:#f4f4f4;padding:20px;'>
              <div style='max-width:600px;margin:0 auto;background:#fff;
                          border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);'>
                <div style='background:{accentColor};padding:24px;text-align:center;'>
                  <h1 style='color:#fff;margin:0;font-size:22px;'>PouleLabApp</h1>
                  <p style='color:rgba(255,255,255,0.85);margin:6px 0 0;'>
                    Gestion des analyses de laboratoire
                  </p>
                </div>
                <div style='padding:32px;'>
                  <p style='color:#374151;font-size:16px;'>Bonjour <strong>{name}</strong>,</p>
                  <p style='color:#374151;font-size:15px;line-height:1.6;'>{mainMessage}</p>
                  <p style='color:#6B7280;font-size:14px;line-height:1.6;'>{subMessage}</p>
                </div>
                <div style='background:#F9FAFB;padding:16px;text-align:center;
                            border-top:1px solid #E5E7EB;'>
                  <p style='color:#9CA3AF;font-size:12px;margin:0;'>
                    Cet email a été envoyé automatiquement par PouleLabApp.<br/>
                    Poulina Group Holding — Tunisie
                  </p>
                </div>
              </div>
            </body>
            </html>";
    }
}