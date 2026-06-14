using PouleLabApp.API.Data;
using PouleLabApp.API.Models;
using PouleLabApp.API.Services.Interfaces;

namespace PouleLabApp.API.Services
{
    // Enregistre chaque action importante sur une demande pour la traçabilité complète
    public class AuditLogService : IAuditLogService
    {
        private readonly ApplicationDbContext _context;

        public AuditLogService(ApplicationDbContext context)
        {
            _context = context;
        }

        public async Task LogAsync(
            int requestId,
            string performedById,
            string action,
            string? oldValue = null,
            string? newValue = null)
        {
            // Créer une entrée dans l'historique
            var log = new AuditLog
            {
                RequestId = requestId,
                PerformedById = performedById,
                EntityType = "AnalysisRequest",
                Action = action,
                OldValue = oldValue,
                NewValue = newValue,
                PerformedAt = DateTime.UtcNow
            };

            _context.AuditLogs.Add(log);
            await _context.SaveChangesAsync();
        }
    }
}