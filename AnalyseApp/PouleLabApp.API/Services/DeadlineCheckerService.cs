using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using PouleLabApp.API.Data;
using PouleLabApp.API.Models;

namespace PouleLabApp.API.Services
{
    public class DeadlineCheckerService : BackgroundService
    {
        private readonly IServiceProvider _serviceProvider;
        private readonly ILogger<DeadlineCheckerService> _logger;

        public DeadlineCheckerService(
            IServiceProvider serviceProvider,
            ILogger<DeadlineCheckerService> logger)
        {
            _serviceProvider = serviceProvider;
            _logger = logger;
        }

        protected override async Task ExecuteAsync(CancellationToken stoppingToken)
        {
            _logger.LogInformation("[DeadlineChecker] Service démarré.");

            while (!stoppingToken.IsCancellationRequested)
            {
                await CheckExpiringDeadlines();
                await Task.Delay(TimeSpan.FromMinutes(1), stoppingToken);
            }
        }

        private async Task CheckExpiringDeadlines()
        {
            using var scope = _serviceProvider.CreateScope();
            var context = scope.ServiceProvider
                .GetRequiredService<ApplicationDbContext>();

            var now = DateTime.UtcNow;

            // Chercher les échantillons périmables dont la date est dépassée
            var expired = await context.Deadlines
                .Include(d => d.Request)
                    .ThenInclude(r => r.Client)
                .Where(d =>
                    d.IsPerishable &&
                    d.ExpiryDate.HasValue &&
                    d.ExpiryDate < now &&
                    d.Request.Status != RequestStatus.Validated &&
                    d.Request.Status != RequestStatus.Closed)
                .ToListAsync();

            if (!expired.Any())
            {
                _logger.LogInformation("[DeadlineChecker] Aucune péremption détectée.");
                return;
            }

            foreach (var deadline in expired)
            {
                // Vérifier si une notification a déjà été envoyée
                var alreadyNotified = await context.Notifications
                    .AnyAsync(n =>
                        n.RequestId == deadline.RequestId &&
                        n.Message.Contains("péremption") &&
                        n.CreatedAt > now.AddHours(-24));

                if (alreadyNotified) continue;

                // Notifier le client
                context.Notifications.Add(new Notification
                {
                    RecipientId = deadline.Request.ClientId,
                    RequestId   = deadline.RequestId,
                    Message     = $"⚠ Alerte péremption — Demande #{deadline.RequestId} : " +
                                  $"un échantillon a dépassé sa date de péremption.",
                    IsRead      = false,
                    CreatedAt   = now
                });

                _logger.LogInformation(
                    "[DeadlineChecker] Péremption détectée — Demande #{Id}",
                    deadline.RequestId);
            }

            await context.SaveChangesAsync();
        }
    }
}