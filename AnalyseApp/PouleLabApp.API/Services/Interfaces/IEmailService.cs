namespace PouleLabApp.API.Services.Interfaces
{
    // Contrat du service d'envoi d'emails
    // Utilisé pour notifier les utilisateurs des changements de statut
    public interface IEmailService
    {
        // Envoyer un email simple avec support HTML
        Task SendEmailAsync(string toEmail, string toName, string subject, string htmlBody);

        // Templates prédéfinis pour chaque événement du workflow
        Task SendRequestSubmittedAsync(string toEmail, string toName, int requestId);
        Task SendRequestReceivedAsync(string toEmail, string toName, int requestId);
        Task SendRequestAssignedAsync(string toEmail, string toName, int requestId);
        Task SendResultsReadyAsync(string toEmail, string toName, int requestId);
        Task SendRequestRejectedAsync(string toEmail, string toName, int requestId, string reason);
        Task SendDeadlineOverdueAsync(string toEmail, string toName, int requestId, string phase);
    }
}