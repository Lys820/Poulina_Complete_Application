using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using PouleLabApp.API.Data;
using PouleLabApp.API.DTOs.Notification;
using PouleLabApp.API.Models;

namespace PouleLabApp.API.Controllers
{
    [ApiController]
    [Route("api/notifications")]
    [Authorize]
    public class NotificationController : ControllerBase
    {
        private readonly ApplicationDbContext _context;
        private readonly UserManager<ApplicationUser> _userManager;

        public NotificationController(
            ApplicationDbContext context,
            UserManager<ApplicationUser> userManager)
        {
            _context = context;
            _userManager = userManager;
        }

        // -------------------------------------------------------
        // GET /api/notifications
        // Récupérer toutes les notifications de l'utilisateur connecté
        // -------------------------------------------------------
        [HttpGet]
        public async Task<IActionResult> GetAll()
        {
            var userId = _userManager.GetUserId(User);

            var notifications = await _context.Notifications
                .Include(n => n.Request)
                .Where(n => n.RecipientId == userId)
                .OrderByDescending(n => n.CreatedAt)
                .Select(n => new NotificationDto
                {
                    Id = n.Id,
                    Message = n.Message,
                    IsRead = n.IsRead,
                    CreatedAt = n.CreatedAt,
                    RequestId = n.RequestId,
                    RequestStatus = n.Request != null ? n.Request.Status.ToString() : "System"
                })
                .ToListAsync();

            return Ok(notifications);
        }

        // -------------------------------------------------------
        // GET /api/notifications/unread
        // Récupérer uniquement les notifications non lues
        // Utilisé par le frontend pour afficher le badge de notifications
        // -------------------------------------------------------
        [HttpGet("unread")]
        public async Task<IActionResult> GetUnread()
        {
            var userId = _userManager.GetUserId(User);

            var notifications = await _context.Notifications
                .Include(n => n.Request)
                .Where(n => n.RecipientId == userId && !n.IsRead)
                .OrderByDescending(n => n.CreatedAt)
                .Select(n => new NotificationDto
                {
                    Id = n.Id,
                    Message = n.Message,
                    IsRead = n.IsRead,
                    CreatedAt = n.CreatedAt,
                    RequestId = n.RequestId,
                   RequestStatus = n.Request != null ? n.Request.Status.ToString() : "System"
                })
                .ToListAsync();

            // Retourner aussi le nombre total pour le badge
            return Ok(new
            {
                count = notifications.Count,
                notifications
            });
        }

        // -------------------------------------------------------
        // PUT /api/notifications/{id}/read
        // Marquer une notification spécifique comme lue
        // -------------------------------------------------------
        [HttpPut("{id}/read")]
        public async Task<IActionResult> MarkAsRead(int id)
        {
            var userId = _userManager.GetUserId(User);

            var notification = await _context.Notifications
                .FirstOrDefaultAsync(n => n.Id == id && n.RecipientId == userId);

            if (notification == null)
                return NotFound(new { message = "Notification introuvable." });

            notification.IsRead = true;
            await _context.SaveChangesAsync();

            return Ok(new { message = "Notification marquée comme lue." });
        }

        // -------------------------------------------------------
        // PUT /api/notifications/read-all
        // Marquer toutes les notifications de l'utilisateur comme lues
        // -------------------------------------------------------
        [HttpPut("read-all")]
        public async Task<IActionResult> MarkAllAsRead()
        {
            var userId = _userManager.GetUserId(User);

            var unreadNotifications = await _context.Notifications
                .Where(n => n.RecipientId == userId && !n.IsRead)
                .ToListAsync();

            if (!unreadNotifications.Any())
                return Ok(new { message = "Aucune notification non lue." });

            foreach (var notification in unreadNotifications)
                notification.IsRead = true;

            await _context.SaveChangesAsync();

            return Ok(new
            {
                message = $"{unreadNotifications.Count} notification(s) marquée(s) comme lues."
            });
        }

        // -------------------------------------------------------
        // DELETE /api/notifications/{id}
        // Supprimer une notification spécifique
        // -------------------------------------------------------
        [HttpDelete("{id}")]
        public async Task<IActionResult> Delete(int id)
        {
            var userId = _userManager.GetUserId(User);

            var notification = await _context.Notifications
                .FirstOrDefaultAsync(n => n.Id == id && n.RecipientId == userId);

            if (notification == null)
                return NotFound(new { message = "Notification introuvable." });

            _context.Notifications.Remove(notification);
            await _context.SaveChangesAsync();

            return Ok(new { message = "Notification supprimée." });
        }

        // -------------------------------------------------------
        // DELETE /api/notifications
        // Supprimer toutes les notifications de l'utilisateur
        // -------------------------------------------------------
        [HttpDelete]
        public async Task<IActionResult> DeleteAll()
        {
            var userId = _userManager.GetUserId(User);

            var notifications = await _context.Notifications
                .Where(n => n.RecipientId == userId)
                .ToListAsync();

            if (!notifications.Any())
                return Ok(new { message = "Aucune notification à supprimer." });

            _context.Notifications.RemoveRange(notifications);
            await _context.SaveChangesAsync();

            return Ok(new
            {
                message = $"{notifications.Count} notification(s) supprimée(s)."
            });
        }
    }
}