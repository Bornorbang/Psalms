# Multi-Role System Implementation Guide

## Overview
The Psalms Real Estate platform now supports multi-role functionality, allowing users to have multiple roles (Tenant, Landlord, Agent) and switch between them seamlessly.

## Features Implemented

### 1. Database Schema (✅ Complete)
- **`User.roles`**: JSONField storing list of user's roles
- **`User.active_role`**: CharField tracking currently active role
- **Helper Methods**:
  - `add_role(role)`: Add new role to user
  - `remove_role(role)`: Remove role (except primary)
  - `switch_role(role)`: Switch active role
  - `is_multi_role`: Check if user has multiple roles
  - `available_roles`: Get list of available roles
  - `has_tenant_role`, `has_landlord_role`, `has_agent_role`: Check role availability

### 2. Role Switching UI (✅ Complete)
- **Location**: Dashboard sidebar (all dashboard pages)
- **Visibility**: Only shows when `user.is_multi_role` is True
- **Design**: 
  - Gradient button with "Switch Role" text
  - Dropdown menu with all available roles
  - Color-coded role icons (Tenant=Blue, Landlord=Green, Agent=Orange)
  - Active role indicator with checkmark
  - Smooth animations and transitions

### 3. Backend Logic (✅ Complete)
- **View**: `switch_role(request, role)` in `app/views.py`
- **URL**: `/dashboard/switch-role/<role>/`
- **Validation**: Checks if role exists and user has permission
- **Redirect**: Auto-redirects to appropriate dashboard after switch
- **Messages**: Success/error feedback via Django messages

### 4. Permission System (✅ Complete)
- **Updated Decorators**: All use `active_role` instead of `role`
- **Decorators Updated**:
  - `@tenant_required`
  - `@landlord_required`
  - `@agent_required`
  - `@super_admin_required`
  - `role_required(*allowed_roles)`

### 5. Auto-Role Detection (✅ Complete)
- **Property Creation**: When landlord creates property, LANDLORD role auto-added
- **Future**: Can extend to rental applications (auto-add TENANT role)

### 6. Admin Interface (✅ Complete)
- **Display**: Shows all roles as colored badges
- **Fields**: Can edit `role`, `roles`, and `active_role`
- **Filter**: Can filter by role or active_role
- **Visual**: Color-coded badges (Blue/Green/Orange/Red)

### 7. Card Styling Updates (✅ Complete)
- **Invoice Cards**: Updated to `p-6`, `gap-6`, `rounded-xl` (matches property page)
- **Payment Cards**: Updated to `p-6`, `gap-6`, `rounded-xl` (matches property page)
- **Consistency**: All dashboard cards now have uniform styling

## How to Use

### For End Users

#### Switching Roles
1. Login to your dashboard
2. Look for the **"Switch Role"** button in the sidebar (blue gradient button)
3. Click to see dropdown of available roles
4. Click desired role to switch
5. Dashboard will reload with new role's view

#### Example Scenario
**User is both Tenant and Landlord:**
- Primary role: TENANT
- Secondary role: LANDLORD (owns 2 properties)
- Active role: TENANT (currently viewing)

**Actions:**
1. User sees "Switch Role" button in sidebar
2. Clicks button, sees:
   - ✓ **Tenant** (Currently Active)
   - **Landlord**
3. Clicks "Landlord"
4. Redirected to Landlord Dashboard
5. Can now manage properties, view landlord-specific features

### For Admins

#### Adding Roles to Users
**Option 1: Django Admin**
1. Go to `/admin/app/user/`
2. Select user
3. Edit "Roles" field (JSON array): `["TENANT", "LANDLORD"]`
4. Save

**Option 2: Management Command**
```bash
python manage.py add_test_role <username> <ROLE>
```
Example:
```bash
python manage.py add_test_role john_doe LANDLORD
```

**Option 3: Python Shell**
```python
from app.models import User

user = User.objects.get(username='john_doe')
user.add_role('LANDLORD')  # Adds LANDLORD role
user.roles  # ['TENANT', 'LANDLORD']
```

#### Removing Roles
```python
user.remove_role('LANDLORD')  # Cannot remove primary role
```

### For Developers

#### Checking User Roles
```python
# Check active role
if request.user.is_tenant:  # True if active_role == TENANT
    # Tenant-specific logic

# Check if user has role (regardless of active)
if request.user.has_landlord_role:  # True if LANDLORD in roles
    # Show landlord features

# Get all roles
user.roles  # ['TENANT', 'LANDLORD']
user.available_roles  # [('TENANT', 'Tenant'), ('LANDLORD', 'Landlord')]
```

#### Auto-Adding Roles
```python
# Example: Add TENANT role when user applies for rental
def rental_application_view(request):
    if request.method == 'POST':
        # ... process application ...
        if User.Role.TENANT not in request.user.roles:
            request.user.add_role(User.Role.TENANT)
            messages.info(request, 'Tenant role added to your account.')
```

## Testing Checklist

### Manual Testing
- [ ] Create user with single role
- [ ] Add second role via admin
- [ ] Verify "Switch Role" button appears
- [ ] Click button, dropdown shows both roles
- [ ] Switch to second role
- [ ] Verify dashboard changes
- [ ] Check sidebar navigation updates
- [ ] Verify permissions work correctly
- [ ] Switch back to primary role
- [ ] Test with 3 roles (Tenant + Landlord + Agent)

### Migration Testing
- [✅] Run migrations successfully
- [✅] Existing users have `roles` populated
- [✅] Existing users have `active_role` set
- [✅] No data loss

### Permission Testing
- [ ] Tenant can only access tenant routes
- [ ] Landlord can only access landlord routes
- [ ] Multi-role user can access both after switching
- [ ] Cannot access role without switching first

## Database Migrations

### Applied Migrations
1. **0011_user_active_role_user_roles**: Added fields
2. **0012_auto_20260414_1756**: Populated roles for existing users

### Schema Changes
```python
# User Model
class User(AbstractUser):
    role = CharField()  # Primary role
    roles = JSONField(default=list)  # ['TENANT', 'LANDLORD']
    active_role = CharField()  # Currently active role
```

## UI Components

### Role Switcher Dropdown
- **Colors**:
  - Button: Gradient from primary to blue-600
  - Tenant Icon: Blue (#3B82F6)
  - Landlord Icon: Green (#10B981)
  - Agent Icon: Orange (#F59E0B)
  - Super Admin Icon: Red (#EF4444)

- **States**:
  - Closed: Chevron down
  - Open: Chevron rotated 180°
  - Active role: Blue background, checkmark
  - Hover: Gray background

### Card Styling
- **Padding**: `p-6` (24px)
- **Border Radius**: `rounded-xl` (12px)
- **Gap**: `gap-6` (24px between cards)
- **Shadow**: `shadow-sm` (small shadow)
- **Hover**: `hover:shadow-md` (medium shadow)

## API Endpoints

### Role Switching
- **URL**: `/dashboard/switch-role/<role>/`
- **Method**: GET (with CSRF protection via login_required)
- **Parameters**: 
  - `role`: TENANT, LANDLORD, AGENT, or SUPER_ADMIN
- **Response**: Redirect to appropriate dashboard
- **Messages**: Success/error feedback

## Configuration

### Settings Required
None - works out of the box!

### Environment Variables
None required for multi-role functionality.

## Troubleshooting

### "Switch Role" button not showing
- **Check**: Does user have multiple roles?
- **Fix**: Add second role via admin or management command

### Cannot switch role
- **Check**: Is role in user's `roles` list?
- **Fix**: Use `user.add_role('ROLE_NAME')`

### Permission denied after switching
- **Check**: Are decorators using `active_role`?
- **Fix**: All decorators updated to use `active_role`

### Roles field empty
- **Check**: Did migration 0012 run?
- **Fix**: Run `python manage.py migrate`

## Future Enhancements

### Planned Features
1. **Auto-detection for Tenant role**: When user applies for rental
2. **Role history tracking**: Log all role switches
3. **Role-specific notifications**: Different alerts per role
4. **Dashboard preview**: See other role's dashboard without switching
5. **Quick switch in header**: Additional switcher in top navigation

### Extension Points
```python
# Add custom role detection
def detect_user_roles(user):
    roles = []
    if RentalAgreement.objects.filter(tenant=user).exists():
        roles.append('TENANT')
    if Property.objects.filter(landlord=user).exists():
        roles.append('LANDLORD')
    return roles
```

## Support

### Common Questions

**Q: Can I remove primary role?**
A: No, primary role (`user.role`) cannot be removed.

**Q: What happens to active_role if I remove it from roles?**
A: System auto-resets to primary role.

**Q: Can agents also be tenants/landlords?**
A: Yes! Agents can have any combination of roles.

**Q: Does role switching affect database queries?**
A: No, all existing data remains. Only view permissions change.

## Version History

### v1.0 (April 14, 2026)
- ✅ Multi-role database schema
- ✅ Role switcher UI component
- ✅ Permission system update
- ✅ Admin interface enhancements
- ✅ Auto-role detection for landlords
- ✅ Card styling consistency
- ✅ Complete migration support

## Credits
Implemented with full frontend, backend, admin, and migration support per user requirements.
