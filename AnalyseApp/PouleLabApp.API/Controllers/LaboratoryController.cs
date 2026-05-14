using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using PouleLabApp.API.Data;

namespace PouleLabApp.API.Controllers
{
    [ApiController]
    [Route("api/laboratories")]
    [Authorize]
    public class LaboratoryController : ControllerBase
    {
        private readonly ApplicationDbContext _context;

        public LaboratoryController(ApplicationDbContext context)
        {
            _context = context;
        }

        // GET /api/laboratories — liste tous les laboratoires
        [HttpGet]
        public async Task<IActionResult> GetAll()
        {
            var labs = await _context.Laboratories
                .Select(l => new {
                    l.Id, l.Name, l.Description, l.Address
                })
                .ToListAsync();

            return Ok(labs);
        }
    }
}