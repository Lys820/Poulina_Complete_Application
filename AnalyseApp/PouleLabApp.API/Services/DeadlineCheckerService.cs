using Microsoft.EntityFrameworkCore;
using PouleLabApp.API.Data;

namespace PouleLabApp.API.Services
{
    // Service d'arrière-plan — vérifie toutes les heures les échéances dépassées
    // Tourne en continu tant que l'application est en cours d'exécution
    public class DeadlineCheckerService : BackgroundService
    {
        // IServiceScopeFactory permet de créer un scope pour accéder au DbContext
        // car les BackgroundService sont des singletons et le DbContext est scoped
        private readonly IServiceScopeFactory _scopeFactory;
        private readonly ILogger<DeadlineCheckerService> _logger;

        public DeadlineCheckerService(
            IServiceScopeFactory scopeFactory,
            ILogger<DeadlineCheckerService> logger)
        {
            _scopeFactory = scopeFactory;
            _logger = logger;
        }

        protected override async Task ExecuteAsync(CancellationToken stoppingToken)
        {
            _logger.LogInformation("[DeadlineChecker] Service démarré.");

            // Boucle infinie — s'arrête quand l'application s'arrête
            while (!stoppingToken.IsCancellationRequested)
            {
                await CheckDeadlinesAsync();

                // Attendre 1 heure avant la prochaine vérification
                await Task.Delay(TimeSpan.FromMinutes(1), stoppingToken);
            }
        }

        private async Task CheckDeadlinesAsync()
        {
            // Créer un nouveau scope pour accéder au DbContext
            using var scope = _scopeFactory.CreateScope();
            var context = scope.ServiceProvider
                .GetRequiredService<ApplicationDbContext>();

            var now = DateTime.UtcNow;

            // Récupérer toutes les échéances non complétées et non encore marquées en retard
            var overdueDeadlines = await context.Deadlines
                .Include(d => d.Request)
                .Where(d =>
                    d.PlannedDate < now &&
                    d.ActualDate == null &&
                    !d.IsOverdue)
                .ToListAsync();

            if (!overdueDeadlines.Any())
            {
                _logger.LogInformation("[DeadlineChecker] Aucun retard détecté.");
                return;
            }

            // Marquer chaque échéance dépassée
            foreach (var deadline in overdueDeadlines)
            {
                deadline.IsOverdue = true;

                _logger.LogWarning(
                    "[DeadlineChecker] Retard détecté — Demande #{RequestId} — Phase {Phase} — Prévue le {PlannedDate}",
                    deadline.RequestId,
                    deadline.Phase,
                    deadline.PlannedDate
                );

                // Créer une notification pour alerter les responsables
                context.Notifications.Add(new Models.Notification
                {
                    RecipientId = deadline.Request.AssignedToId
                        ?? deadline.Request.ClientId,
                    RequestId = deadline.RequestId,
                    Message = $"Retard détecté sur la demande #{deadline.RequestId} — Phase {deadline.Phase} dépassée depuis le {deadline.PlannedDate:dd/MM/yyyy}.",
                    IsRead = false,
                    CreatedAt = now
                });
            }

            await context.SaveChangesAsync();

            _logger.LogInformation(
                "[DeadlineChecker] {Count} retard(s) marqué(s).",
                overdueDeadlines.Count
            );
        }
    }
}