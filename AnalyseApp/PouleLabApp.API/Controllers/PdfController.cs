using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using PouleLabApp.API.Services.Interfaces;

namespace PouleLabApp.API.Controllers
{
    [ApiController]
    [Route("api/requests")]
    [Authorize]
    public class PdfController : ControllerBase
    {
        private readonly IPdfService _pdfService;

        public PdfController(IPdfService pdfService)
        {
            _pdfService = pdfService;
        }

        // -------------------------------------------------------
        // GET /api/requests/{id}/pdf
        // Télécharger le formulaire de demande en PDF
        // Accessible à tous les rôles connectés
        // -------------------------------------------------------
        [HttpGet("{id}/pdf")]
        public IActionResult DownloadRequestForm(int id)
        {
            var pdfBytes = _pdfService.GenerateRequestFormPdf(id);

            // Retourner le fichier PDF avec le bon Content-Type
            return File(
                pdfBytes,
                "application/pdf",
                $"demande-{id}.pdf"
            );
        }

        // -------------------------------------------------------
        // GET /api/requests/{id}/bulletin
        // Télécharger le bulletin d'analyses en PDF
        // Accessible uniquement si la demande est validée
        // -------------------------------------------------------
        [HttpGet("{id}/bulletin")]
        public IActionResult DownloadBulletin(int id)
        {
            var pdfBytes = _pdfService.GenerateBulletinPdf(id);

            return File(
                pdfBytes,
                "application/pdf",
                $"bulletin-analyses-{id}.pdf"
            );
        }
    }
}