using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using PouleLabApp.API.Data;

namespace PouleLabApp.API.Controllers
{
    [ApiController]
    [Route("api/analysistypes")]
    [Authorize]
    public class AnalysisTypeController : ControllerBase
    {
        private readonly ApplicationDbContext _context;

        public AnalysisTypeController(ApplicationDbContext context)
        {
            _context = context;
        }

        // GET /api/analysistypes — liste tous les types d'analyses
        [HttpGet]
        public async Task<IActionResult> GetAll()
        {
            var types = await _context.AnalysisTypes
                .Select(t => new {
                    t.Id, t.Name, t.Description,
                    t.ReferenceMin, t.ReferenceMax, t.Unit
                })
                .ToListAsync();

            return Ok(types);
        }
    }
}