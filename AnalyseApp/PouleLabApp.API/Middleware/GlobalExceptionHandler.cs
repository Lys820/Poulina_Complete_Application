using System.Net;
using System.Text.Json;

namespace PouleLabApp.API.Middleware
{
    // Middleware global qui intercepte toutes les exceptions non gérées
    // Sans ce middleware, une erreur serveur retourne une page HTML illisible côté Angular
    public class GlobalExceptionHandler
    {
        // _next représente le prochain middleware dans la pipeline HTTP
        private readonly RequestDelegate _next;
        private readonly ILogger<GlobalExceptionHandler> _logger;

        public GlobalExceptionHandler(
            RequestDelegate next,
            ILogger<GlobalExceptionHandler> logger)
        {
            _next = next;
            _logger = logger;
        }

        public async Task InvokeAsync(HttpContext context)
        {
            try
            {
                // Laisser passer la requête normalement
                await _next(context);
            }
            catch (Exception ex)
            {
                // Logger l'erreur complète côté serveur pour le débogage
                _logger.LogError(ex, "Une erreur inattendue s'est produite.");

                // Retourner une réponse JSON propre au client
                await HandleExceptionAsync(context, ex);
            }
        }

        private static async Task HandleExceptionAsync(HttpContext context, Exception ex)
        {
            context.Response.ContentType = "application/json";

            // Adapter le code HTTP selon le type d'erreur
            context.Response.StatusCode = ex switch
            {
                UnauthorizedAccessException => (int)HttpStatusCode.Unauthorized,   // 401
                ArgumentException => (int)HttpStatusCode.BadRequest,               // 400
                KeyNotFoundException => (int)HttpStatusCode.NotFound,              // 404
                _ => (int)HttpStatusCode.InternalServerError                       // 500 par défaut
            };

            // Corps de la réponse JSON — on ne renvoie jamais la stack trace en production
            var response = new
            {
                status = context.Response.StatusCode,
                message = "Une erreur inattendue s'est produite. Veuillez réessayer.",
                detail = ex.Message // En production, supprimer cette ligne pour ne pas exposer les détails
            };

            var json = JsonSerializer.Serialize(response);
            await context.Response.WriteAsync(json);
        }
    }
}