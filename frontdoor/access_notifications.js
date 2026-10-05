// Access requests are application workflow; memberships and recipients come from Clerk.
export async function notifyOrganizationAdmins(item, association, env, client, appOrigin) {
  const previous = item.notification || {};
  if (previous.status === "sent") return previous;
  const result = {status: "not_configured", sent_user_ids: previous.sent_user_ids || [], attempted_at: new Date().toISOString()};
  if (!env.ACCESS_REQUEST_EMAIL?.send || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(env.ACCESS_REQUEST_FROM || "")) return result;
  try {
    const admins = [];
    for (let offset = 0; ; offset += 100) {
      const page = await client.organizations.getOrganizationMembershipList({organizationId: association.clerk_organization_id, limit: 100, offset});
      admins.push(...page.data.filter(member => member.role === "org:admin" || member.permissions?.includes("org:sys_memberships:manage")));
      if (!page.data.length || offset + page.data.length >= page.totalCount) break;
    }
    const ids = [...new Set(admins.map(member => member.publicUserData?.userId).filter(Boolean))];
    if (!ids.length) return {...result, status: "no_admins"};
    result.status = "sent";
    for (const userId of ids) {
      if (result.sent_user_ids.includes(userId)) continue;
      try {
        const user = await client.users.getUser(userId);
        const email = user.emailAddresses?.find(value => value.id === user.primaryEmailAddressId && value.verification?.status === "verified")?.emailAddress;
        if (!email || user.banned || user.locked) { result.status = "failed"; continue; }
        const name = association.display_name || association.tenant_id;
        const text = `${item.email} has requested access to ${name}.\n\nOpen Rental Desk, select the organization with your authentication provider, and open Admin Center to review the request. Invite the user or manage their role with your authentication provider.\n\n${appOrigin}/?view=admin\n\nRequest: ${item.id}\n\n${item.email} hat Zugriff auf ${name} angefragt. Bitte öffne die Verwaltung in Rental Desk und verwalte die Mitgliedschaft beim Anmeldeanbieter.`;
        await env.ACCESS_REQUEST_EMAIL.send({
          from: {email: env.ACCESS_REQUEST_FROM, name: "Rental Desk"},
          to: email,
          subject: "Rental Desk: association access request / Zugangsanfrage",
          text,
          html: `<p>${text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll("\n", "<br>")}</p>`
        });
        result.sent_user_ids.push(userId);
      } catch {
        result.status = "failed";
      }
    }
    return result;
  } catch {
    return {...result, status: "failed"};
  }
}

export function notificationSummary(item) {
  return item.notification?.status || "not_configured";
}
