using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace PouleLabApp.API.Migrations
{
    /// <inheritdoc />
    public partial class AddApprovalAndLabToUser : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<bool>(
                name: "IsApproved",
                table: "AspNetUsers",
                type: "bit",
                nullable: false,
                defaultValue: false);

            migrationBuilder.AddColumn<int>(
                name: "LaboratoryId",
                table: "AspNetUsers",
                type: "int",
                nullable: true);

            migrationBuilder.CreateIndex(
                name: "IX_AspNetUsers_LaboratoryId",
                table: "AspNetUsers",
                column: "LaboratoryId");

            migrationBuilder.AddForeignKey(
                name: "FK_AspNetUsers_Laboratories_LaboratoryId",
                table: "AspNetUsers",
                column: "LaboratoryId",
                principalTable: "Laboratories",
                principalColumn: "Id");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_AspNetUsers_Laboratories_LaboratoryId",
                table: "AspNetUsers");

            migrationBuilder.DropIndex(
                name: "IX_AspNetUsers_LaboratoryId",
                table: "AspNetUsers");

            migrationBuilder.DropColumn(
                name: "IsApproved",
                table: "AspNetUsers");

            migrationBuilder.DropColumn(
                name: "LaboratoryId",
                table: "AspNetUsers");
        }
    }
}
