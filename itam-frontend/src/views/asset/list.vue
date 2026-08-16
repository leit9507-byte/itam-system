<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">资产管理</h2>
        <p class="page-subtitle">支持批量导入、批量编辑、批量维修、出入库、责任人绑定、供应商关联和报废处置登记</p>
      </div>
      <div class="header-actions">
        <el-button @click="downloadAssetCsv">导出资产台账</el-button>
        <el-button @click="downloadTemplate">下载导入模板</el-button>
        <el-button type="primary" @click="openImportDialog">批量导入资产</el-button>
      </div>
    </div>

    <el-card shadow="never">
      <div class="toolbar">
        <el-input v-model="filters.keyword" clearable placeholder="搜索资产编码/名称/部门/序列号/使用人/供应商/备注" style="width: 400px" @input="refreshAssets" />
        <el-select v-model="filters.status" clearable placeholder="状态" style="width: 140px" @change="refreshAssets">
          <el-option v-for="item in assetStatuses" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.category" clearable filterable placeholder="设备类型" style="width: 160px" @change="refreshAssets">
          <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filters.company" clearable filterable placeholder="公司" style="width: 180px" @change="refreshAssets">
          <el-option label="未设置公司" value="未设置公司" />
          <el-option v-for="item in realCompanies" :key="item.id || item.name" :label="item.name" :value="item.name" />
        </el-select>
        <el-select v-model="filters.supplier" clearable filterable placeholder="供应商" style="width: 180px" @change="refreshAssets">
          <el-option v-for="item in suppliers" :key="item.id || item.name" :label="item.name" :value="item.name" />
        </el-select>
        <el-select v-model="filters.risk_filter" clearable placeholder="风险筛选" style="width: 210px" @change="refreshAssets">
          <el-option label="仍在使用且已过保" value="active_warranty_overdue" />
          <el-option label="仍在使用且超服役" value="active_retirement_overdue" />
          <el-option label="仍在使用且过保/超服役" value="active_warranty_or_retirement_overdue" />
        </el-select>
        <el-divider direction="vertical" />
        <el-button :disabled="!selected.length" @click="openBatchEdit">批量编辑</el-button>
        <el-button :disabled="!selected.length" @click="openBatchRepair">批量维修</el-button>
        <el-button :disabled="!selected.length" @click="openBatch('inbound')">批量入库</el-button>
        <el-button :disabled="!selected.length" @click="openBatch('outbound')">批量出库</el-button>
        <el-button type="danger" :disabled="!selected.length" @click="openBatch('scrap')">批量申请报废</el-button>
        <el-button @click="columnDialog.visible = true">字段设置</el-button>
      </div>
    </el-card>

    <el-alert
      v-if="workflowHint"
      :title="workflowHint"
      type="warning"
      show-icon
      class="workflow-alert"
      @close="workflowHint = ''"
    />

    <el-card shadow="never">
      <el-alert v-if="selected.length" :title="`已选择 ${selected.length} 个资产`" type="info" show-icon :closable="false" class="selection-alert" />
      <el-table ref="assetTableRef" :data="assets" border stripe row-key="asset_id" :reserve-selection="true" @selection-change="selected = $event">
        <el-table-column type="selection" width="48" reserve-selection />
        <template v-for="column in orderedAssetColumns" :key="column.key">
          <el-table-column v-if="column.key === 'product'" label="产品信息" min-width="240">
            <template #default="{ row }">
              <div class="asset-name">
                <strong>{{ row.name }}</strong>
                <span>{{ row.brand || '-' }} / {{ row.model || '-' }} / {{ row.spec || '-' }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column v-else-if="column.key === 'retirement_years'" prop="retirement_years" label="退役年限" width="100">
            <template #default="{ row }">{{ row.retirement_years ? `${row.retirement_years} 年` : '-' }}</template>
          </el-table-column>
          <el-table-column v-else-if="column.key === 'retirement_date'" prop="retirement_date" label="预计退役时间" width="130">
            <template #default="{ row }">{{ row.retirement_date || '-' }}</template>
          </el-table-column>
          <el-table-column v-else-if="column.key === 'owner'" label="使用人" width="150">
            <template #default="{ row }">{{ displayUser(row) }}</template>
          </el-table-column>
          <el-table-column v-else-if="column.key === 'dept'" label="部门" width="140">
            <template #default="{ row }">{{ displayDept(row) }}</template>
          </el-table-column>
          <el-table-column v-else-if="column.key === 'status'" prop="status" label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="statusMap[row.status]?.type || 'info'">{{ statusMap[row.status]?.label || row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column v-else-if="column.key === 'price'" prop="price" label="价值" width="120">
            <template #default="{ row }">¥{{ Number(row.price || 0).toLocaleString() }}</template>
          </el-table-column>
          <el-table-column v-else-if="column.key === 'current_residual_value'" prop="current_residual_value" label="当前残值" width="120">
            <template #default="{ row }">¥{{ Number(row.current_residual_value || 0).toLocaleString() }}</template>
          </el-table-column>
          <el-table-column v-else :prop="column.prop" :label="column.label" :width="column.width" :min-width="column.minWidth" :show-overflow-tooltip="column.tooltip" />
        </template>
        <el-table-column label="操作" width="270" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="goDetail(row)">详细</el-button>
            <el-button type="primary" link @click="openEdit(row)">编辑</el-button>
            <el-button type="primary" link :disabled="!canInbound(row)" @click="openSingleInbound(row)">入库</el-button>
            <el-button type="warning" link :disabled="!canOutbound(row)" @click="openSingleOutbound(row)">出库</el-button>
            <el-dropdown trigger="click" @command="command => handleMoreCommand(command, row)">
              <el-button type="primary" link>
                更多<el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="repair" :disabled="!canRepair(row)">维修</el-dropdown-item>
                  <el-dropdown-item command="scrap" :disabled="!canScrap(row)">报废</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleAssetPageSizeChange"
          @current-change="loadAssets"
        />
      </div>
    </el-card>

    <el-dialog v-model="editDialog.visible" title="调整资产信息" width="min(900px, calc(100vw - 24px))" class="asset-edit-dialog">
      <el-form :model="editDialog.form" label-width="112px">
        <div class="edit-grid">
          <el-form-item label="产品档案">
            <el-select v-model="editDialog.form.product_id" filterable clearable placeholder="选择产品后自动带出规格" style="width: 100%" @change="applyProductToEdit">
              <el-option v-for="item in products" :key="item.id" :label="`${item.product_name} / ${item.model || '-'} / ${item.spec || '-'}`" :value="item.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="资产编码"><el-input v-model="editDialog.form.asset_id" placeholder="业务编码，例如 ITAM-000001" /></el-form-item>
          <el-form-item label="资产名称"><el-input v-model="editDialog.form.name" /></el-form-item>
          <el-form-item label="所属公司">
            <el-select v-model="editDialog.form.company" filterable clearable style="width: 100%">
              <el-option v-for="item in realCompanies" :key="item.id || item.name" :label="item.name" :value="item.name" />
            </el-select>
          </el-form-item>
          <el-form-item label="序列号"><el-input v-model="editDialog.form.sn" /></el-form-item>
          <el-form-item label="设备类型">
            <el-select v-model="editDialog.form.category" filterable allow-create default-first-option style="width: 100%">
              <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态（流程控制）">
            <el-select v-model="editDialog.form.status" disabled style="width: 100%">
              <el-option v-for="item in manualStatusOptions(editDialog.form.status)" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="品牌"><el-input v-model="editDialog.form.brand" /></el-form-item>
          <el-form-item label="型号"><el-input v-model="editDialog.form.model" /></el-form-item>
          <el-form-item label="规格"><el-input v-model="editDialog.form.spec" /></el-form-item>
          <el-form-item label="价值"><el-input-number v-model="editDialog.form.price" :min="0" :precision="2" style="width: 100%" /></el-form-item>
          <el-form-item label="采购时间"><el-date-picker v-model="editDialog.form.purchase_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item>
          <el-form-item label="采购审批单号"><el-input v-model="editDialog.form.purchase_approval_no" /></el-form-item>
          <el-form-item label="采购供应商">
            <el-select v-model="editDialog.form.purchase_supplier_name" filterable clearable allow-create default-first-option style="width: 100%">
              <el-option v-for="item in suppliers" :key="item.id || item.name" :label="item.name" :value="item.name" />
            </el-select>
          </el-form-item>
          <el-form-item label="维保年限"><el-input-number v-model="editDialog.form.warranty_years" :min="0" :step="1" :precision="0" style="width: 100%" /></el-form-item>
          <el-form-item label="维保到期"><el-input :model-value="warrantyExpirePreview(editDialog.form)" disabled placeholder="根据采购时间和维保年限自动计算" /></el-form-item>
          <el-form-item label="退役年限"><el-input-number v-model="editDialog.form.retirement_years" :min="0" :step="1" :precision="0" style="width: 100%" /></el-form-item>
          <el-form-item label="预计退役时间"><el-input :model-value="retirementDatePreview(editDialog.form)" disabled placeholder="根据采购时间和退役年限自动计算" /></el-form-item>
          <el-form-item label="责任人">
            <el-select
              v-model="editDialog.form.owner_user_id"
              filterable
              remote
              clearable
              reserve-keyword
              :remote-method="searchUsers"
              style="width: 100%"
              @visible-change="visible => visible && searchUsers('')"
              @change="userId => fillUserToForm(editDialog.form, userId)"
            >
              <el-option v-for="user in filteredUsers" :key="user.user_id" :label="userLabel(user)" :value="user.user_id" />
            </el-select>
          </el-form-item>
          <el-form-item label="部门"><el-input v-model="editDialog.form.dept_id" disabled /></el-form-item>
          <el-form-item label="位置">
            <el-select v-model="editDialog.form.location" filterable clearable style="width: 100%">
              <el-option v-for="item in activeLocations" :key="item.id || item.name" :label="locationLabel(item)" :value="item.name" />
            </el-select>
          </el-form-item>
          <el-form-item label="备注" class="edit-grid-wide"><el-input v-model="editDialog.form.remark" type="textarea" :rows="3" placeholder="特殊说明，例如备用机、涉密、借测、待补配件" /></el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="editDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="editDialog.saving" @click="submitEdit">保存调整</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="columnDialog.visible" title="资产列表字段设置" width="560px">
      <el-alert title="勾选需要展示的字段，并可调整展示顺序；选择列和操作列固定显示。" type="info" show-icon :closable="false" class="dialog-alert" />
      <div class="column-order-list">
        <div v-for="(column, index) in configurableAssetColumns" :key="column.key" class="column-order-row">
          <el-checkbox
            :model-value="columnVisibility[column.key] !== false"
            :disabled="visibleColumnCount === 1 && columnVisibility[column.key] !== false"
            @change="value => toggleColumn(column.key, value)"
          >
            {{ index + 1 }}. {{ column.label }}
          </el-checkbox>
          <div>
            <el-button size="small" :disabled="index === 0" @click="moveColumn(index, -1)">上移</el-button>
            <el-button size="small" :disabled="index === configurableAssetColumns.length - 1" @click="moveColumn(index, 1)">下移</el-button>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="resetColumnSettings">恢复默认</el-button>
        <el-button type="primary" @click="columnDialog.visible = false">完成</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="batchEdit.visible" title="批量编辑资产" width="960px">
      <el-alert :title="`本次将更新 ${selected.length} 个资产；未勾选的字段不会覆盖原资产信息。`" type="info" show-icon :closable="false" />
      <div class="batch-edit-toolbar">
        <span>已勾选 {{ batchEditSelectedCount }} 个字段</span>
        <el-button text type="primary" :disabled="!batchEditSelectedCount" @click="resetBatchEditFields">清空勾选</el-button>
      </div>
      <el-form :model="batchEdit.form" label-width="118px" class="batch-form">
        <div class="batch-edit-grid">
          <el-checkbox v-model="batchEdit.fields.name">资产名称</el-checkbox>
          <el-input v-model="batchEdit.form.name" :disabled="!batchEdit.fields.name" />

          <el-checkbox v-model="batchEdit.fields.company">所属公司</el-checkbox>
          <el-select v-model="batchEdit.form.company" filterable clearable :disabled="!batchEdit.fields.company">
            <el-option v-for="item in realCompanies" :key="item.id || item.name" :label="item.name" :value="item.name" />
          </el-select>

          <el-checkbox v-model="batchEdit.fields.sn">序列号</el-checkbox>
          <el-input v-model="batchEdit.form.sn" :disabled="!batchEdit.fields.sn" />

          <el-checkbox v-model="batchEdit.fields.category">设备类型</el-checkbox>
          <el-select v-model="batchEdit.form.category" filterable allow-create default-first-option :disabled="!batchEdit.fields.category">
            <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
          </el-select>

          <el-checkbox v-model="batchEdit.fields.status">状态</el-checkbox>
          <el-select v-model="batchEdit.form.status" :disabled="!batchEdit.fields.status">
            <el-option v-for="item in editableAssetStatuses" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>

          <el-checkbox v-model="batchEdit.fields.brand">品牌</el-checkbox>
          <el-input v-model="batchEdit.form.brand" :disabled="!batchEdit.fields.brand" />

          <el-checkbox v-model="batchEdit.fields.model">型号</el-checkbox>
          <el-input v-model="batchEdit.form.model" :disabled="!batchEdit.fields.model" />

          <el-checkbox v-model="batchEdit.fields.spec">规格</el-checkbox>
          <el-input v-model="batchEdit.form.spec" :disabled="!batchEdit.fields.spec" />

          <el-checkbox v-model="batchEdit.fields.price">价值</el-checkbox>
          <el-input-number v-model="batchEdit.form.price" :min="0" :disabled="!batchEdit.fields.price" style="width: 100%" />

          <el-checkbox v-model="batchEdit.fields.purchase_date">采购时间</el-checkbox>
          <el-date-picker v-model="batchEdit.form.purchase_date" type="date" value-format="YYYY-MM-DD" :disabled="!batchEdit.fields.purchase_date" style="width: 100%" />

          <el-checkbox v-model="batchEdit.fields.purchase_approval_no">审批单号</el-checkbox>
          <el-input v-model="batchEdit.form.purchase_approval_no" :disabled="!batchEdit.fields.purchase_approval_no" />

          <el-checkbox v-model="batchEdit.fields.purchase_supplier_name">供应商</el-checkbox>
          <el-select v-model="batchEdit.form.purchase_supplier_name" filterable clearable allow-create default-first-option :disabled="!batchEdit.fields.purchase_supplier_name">
            <el-option v-for="item in suppliers" :key="item.id || item.name" :label="supplierLabel(item)" :value="item.name" />
          </el-select>

          <el-checkbox v-model="batchEdit.fields.warranty_years">维保年限</el-checkbox>
          <el-input-number v-model="batchEdit.form.warranty_years" :min="0" :step="1" :precision="0" :disabled="!batchEdit.fields.warranty_years" style="width: 100%" />

          <el-checkbox v-model="batchEdit.fields.retirement_years">退役年限</el-checkbox>
          <el-input-number v-model="batchEdit.form.retirement_years" :min="0" :step="1" :precision="0" :disabled="!batchEdit.fields.retirement_years" style="width: 100%" />

          <el-checkbox v-model="batchEdit.fields.owner_user_id">责任人</el-checkbox>
          <el-select v-model="batchEdit.form.owner_user_id" filterable remote clearable reserve-keyword :remote-method="searchUsers" :disabled="!batchEdit.fields.owner_user_id" @change="fillUserToForm(batchEdit.form, $event)">
            <el-option v-for="user in filteredUsers" :key="user.user_id" :label="userLabel(user)" :value="user.user_id" />
          </el-select>

          <el-checkbox v-model="batchEdit.fields.dept_id">部门</el-checkbox>
          <el-input v-model="batchEdit.form.dept_id" :disabled="!batchEdit.fields.dept_id" />

          <el-checkbox v-model="batchEdit.fields.location">位置</el-checkbox>
          <el-select v-model="batchEdit.form.location" filterable clearable :disabled="!batchEdit.fields.location">
            <el-option v-for="item in activeLocations" :key="item.id || item.name" :label="locationLabel(item)" :value="item.name" />
          </el-select>

          <el-checkbox v-model="batchEdit.fields.remark">备注</el-checkbox>
          <el-input v-model="batchEdit.form.remark" type="textarea" :rows="2" :disabled="!batchEdit.fields.remark" />
        </div>
      </el-form>
      <template #footer>
        <el-button @click="batchEdit.visible = false">取消</el-button>
        <el-button type="primary" :disabled="!batchEditSelectedCount" @click="submitBatchEdit">确认批量更新</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="batch.visible" :title="batchTitle" width="660px">
      <el-alert
        :title="batch.type === 'scrap' ? `本次将提交 ${batch.assets.length} 个资产进入待处置登记` : `本次将处理 ${batch.assets.length} 个资产`"
        :description="batch.type === 'scrap' ? '此阶段不填写退役时间、审批单号、处置方式、残值或处置说明；后续在报废处置登记中逐台填写。' : ''"
        :type="batch.type === 'scrap' ? 'warning' : 'info'"
        show-icon
        :closable="false"
      />
      <el-table v-if="batch.type === 'scrap'" :data="batch.assets" border stripe max-height="300" class="scrap-confirm-table">
        <el-table-column prop="display_id" label="序号" width="80" />
        <el-table-column prop="asset_no" label="资产编号" min-width="160" />
        <el-table-column prop="name" label="资产名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="sn" label="序列号" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.sn || '-' }}</template>
        </el-table-column>
      </el-table>
      <el-form v-if="batch.type !== 'scrap'" :model="batch.form" label-width="110px" class="batch-form">
        <template v-if="batch.type === 'inbound'">
          <el-form-item label="入库地址" required>
            <el-select v-model="batch.form.location" filterable clearable style="width: 100%" placeholder="选择入库地址">
              <el-option v-for="item in activeLocations" :key="item.id || item.name" :label="locationLabel(item)" :value="item.name" />
            </el-select>
          </el-form-item>
          <el-form-item label="备注"><el-input v-model="batch.form.remark" type="textarea" :rows="3" placeholder="例如：归还入库、调拨回库" /></el-form-item>
        </template>
        <template v-if="batch.type === 'outbound'">
          <el-form-item label="出库类型">
            <el-select v-model="batch.form.toStatus" style="width: 100%" @change="handleOutboundStatusChange">
              <el-option label="领用在用" value="in_use" />
              <el-option label="借出" value="borrowed" />
              <el-option label="已出库" value="out_stock" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="batch.form.toStatus === 'out_stock'" label="出库对象">
            <el-segmented v-model="batch.form.outboundTarget" :options="outboundTargetOptions" @change="handleOutboundTargetChange" />
          </el-form-item>
          <el-form-item v-if="batch.form.outboundTarget !== 'location'" :label="batch.form.toStatus === 'borrowed' ? '借用人' : '领用人'" required>
            <el-select v-model="batch.form.owner_user_id" filterable remote reserve-keyword style="width: 100%" placeholder="搜索用户姓名/账号/部门" :remote-method="searchUsers" @change="fillUserToForm(batch.form, $event)">
              <el-option v-for="user in filteredUsers" :key="user.user_id" :label="userLabel(user)" :value="user.user_id" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="batch.form.toStatus === 'borrowed'" label="借用到期" required>
            <el-date-picker v-model="batch.form.borrow_due_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" placeholder="选择借用到期时间" />
          </el-form-item>
          <el-form-item v-if="batch.form.outboundTarget !== 'location'" label="部门"><el-input v-model="batch.form.dept_id" disabled /></el-form-item>
          <el-form-item :label="batch.form.outboundTarget === 'location' ? '出库地址' : '使用位置'" :required="batch.form.outboundTarget === 'location'">
            <el-select v-model="batch.form.location" filterable clearable style="width: 100%" placeholder="选择地址">
              <el-option v-for="item in activeLocations" :key="item.id || item.name" :label="locationLabel(item)" :value="item.name" />
            </el-select>
          </el-form-item>
          <el-form-item label="意图说明">
            <el-input v-model="batch.form.remark" type="textarea" :rows="3" placeholder="例如：入职资产分配、临时借用、项目领用" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="batch.visible = false">取消</el-button>
        <el-button type="primary" @click="submitBatch">{{ batch.type === 'scrap' ? '确认提交' : '确认执行' }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="repairDialog.visible" :title="repairDialog.assets.length > 1 ? '批量新增维修记录' : '新增维修记录'" width="620px">
      <el-alert v-if="repairDialog.assets.length > 1" :title="`本次将为 ${repairDialog.assets.length} 个资产创建维修记录，并更新为维修中。`" type="warning" show-icon :closable="false" class="dialog-alert" />
      <el-descriptions v-else-if="repairDialog.asset" :column="2" border class="repair-asset">
        <el-descriptions-item label="序号">{{ repairDialog.asset.display_id || '-' }}</el-descriptions-item>
        <el-descriptions-item label="资产编号">{{ repairDialog.asset.asset_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="资产名称">{{ repairDialog.asset.name }}</el-descriptions-item>
        <el-descriptions-item label="序列号">{{ repairDialog.asset.sn || '-' }}</el-descriptions-item>
        <el-descriptions-item label="当前状态">{{ statusMap[repairDialog.asset.status]?.label || repairDialog.asset.status }}</el-descriptions-item>
      </el-descriptions>
      <el-form :model="repairDialog.form" label-width="100px" class="repair-form">
        <el-form-item label="维修时间" required>
          <el-date-picker v-model="repairDialog.form.repair_time" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="维修类型" required>
          <el-select v-model="repairDialog.form.repair_type" style="width: 100%">
            <el-option label="普通维修" value="普通维修" />
            <el-option label="在保维修" value="在保维修" />
            <el-option label="内部维修" value="内部维修" />
            <el-option label="外部付费维修" value="外部付费维修" />
            <el-option label="返厂维修" value="返厂维修" />
          </el-select>
        </el-form-item>
        <el-form-item label="故障原因" required>
          <el-select v-model="repairDialog.form.fault_reason" filterable clearable allow-create default-first-option placeholder="选择或输入故障类型" style="width: 100%">
            <el-option v-for="item in activeFaultTypes" :key="item.id || item.name" :label="item.name" :value="item.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="维修费用" required>
          <el-input-number v-model="repairDialog.form.repair_cost" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="维修商"><el-input v-model="repairDialog.form.vendor" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="repairDialog.form.remark" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="repairDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitRepair">创建维修单</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importDialog.visible" title="批量导入资产" width="1080px" :before-close="beforeCloseImportDialog" :close-on-click-modal="!importDialog.importing" :close-on-press-escape="!importDialog.importing">
      <el-alert title="导入会按资产状态自动补建借用/出库、维修或报废处置流程；重复导入不会重复建单。" type="info" show-icon :closable="false" />
      <div class="upload-row">
        <el-upload :show-file-list="false" accept=".xlsx,.xlsm" :before-upload="previewExcelImport" :disabled="importDialog.importing">
          <el-button type="primary">上传并预览 Excel</el-button>
        </el-upload>
        <el-button :disabled="importDialog.importing" @click="downloadTemplate">下载导入模板</el-button>
        <el-button :disabled="importDialog.importing" @click="fillImportExample">填入粘贴示例</el-button>
        <el-checkbox v-model="importDialog.overwrite" :disabled="importDialog.importing" @change="clearImportPreview">覆盖已有资产</el-checkbox>
      </div>
      <el-input v-model="importDialog.content" type="textarea" :rows="9" class="import-textarea" placeholder="也可以把 Excel 表格复制后粘贴到这里" :disabled="importDialog.importing" @input="clearImportPreview" />
      <div class="import-actions">
        <el-button :loading="importDialog.loading" :disabled="importDialog.importing" @click="previewTextImport">预览粘贴内容</el-button>
        <el-button type="primary" :disabled="!canConfirmImport" :loading="importDialog.importing" @click="confirmImport">确认导入</el-button>
      </div>
      <section v-if="importDialog.progress.status !== 'idle'" class="import-progress-panel">
        <div class="import-progress-heading">
          <div>
            <strong>{{ importProgressTitle }}</strong>
            <span>{{ importDialog.progress.message }}</span>
          </div>
          <el-tag :type="importProgressTagType">{{ importProgressStatusLabel }}</el-tag>
        </div>
        <el-progress
          :percentage="importProgressPercentage"
          :status="importProgressBarStatus"
          :stroke-width="12"
        />
        <div class="import-progress-stats">
          <span>总数 <strong>{{ importDialog.progress.total }}</strong></span>
          <span>已处理 <strong>{{ importDialog.progress.processed }}</strong></span>
          <span>新增 <strong>{{ importDialog.progress.created }}</strong></span>
          <span>更新 <strong>{{ importDialog.progress.updated }}</strong></span>
          <span>跳过 <strong>{{ importDialog.progress.skipped }}</strong></span>
          <span>失败 <strong class="import-failed-count">{{ importDialog.progress.failed }}</strong></span>
        </div>
        <div v-if="importDialog.progress.totalBatches" class="import-progress-batch">
          当前批次 {{ Math.min(importDialog.progress.currentBatch, importDialog.progress.totalBatches) }} / {{ importDialog.progress.totalBatches }}
          <span>每批最多 {{ IMPORT_CHUNK_SIZE }} 条</span>
        </div>
      </section>
      <el-descriptions v-if="importDialog.preview" :column="3" border class="import-result">
        <el-descriptions-item label="总行数">{{ importDialog.preview.total }}</el-descriptions-item>
        <el-descriptions-item label="可导入">{{ importDialog.preview.valid }}</el-descriptions-item>
        <el-descriptions-item label="错误">{{ importDialog.preview.errors.length }}</el-descriptions-item>
      </el-descriptions>
      <div v-if="importDialog.preview?.items?.length > IMPORT_PREVIEW_LIMIT" class="import-preview-note">
        为保持页面流畅，仅展示前 {{ IMPORT_PREVIEW_LIMIT }} 行；确认导入仍会处理全部 {{ importDialog.preview.valid }} 条有效数据。
      </div>
      <el-table v-if="importDialog.preview?.items?.length" :data="importPreviewRows" border size="small" class="import-result" max-height="320">
        <el-table-column prop="row" label="行号" width="70" />
        <el-table-column label="校验" width="90">
          <template #default="{ row }">
            <el-tag :type="row.valid ? 'success' : 'danger'">{{ row.valid ? '通过' : '错误' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="资产名称" min-width="160"><template #default="{ row }">{{ row.data.name || '-' }}</template></el-table-column>
        <el-table-column label="类型" width="120"><template #default="{ row }">{{ row.data.category || '-' }}</template></el-table-column>
        <el-table-column label="序列号" width="150"><template #default="{ row }">{{ row.data.sn || '-' }}</template></el-table-column>
        <el-table-column label="状态" width="120"><template #default="{ row }">{{ statusMap[row.data.status]?.label || row.data.status || '-' }}</template></el-table-column>
        <el-table-column label="二维码内容" min-width="180"><template #default="{ row }">{{ row.data.scan_codes?.join('；') || '-' }}</template></el-table-column>
        <el-table-column label="责任人/位置" min-width="160"><template #default="{ row }">{{ row.data.owner_user_id || row.data.location || '-' }}</template></el-table-column>
        <el-table-column label="采购价格" width="120"><template #default="{ row }">¥{{ Number(row.data.purchase_price || 0).toLocaleString() }}</template></el-table-column>
      </el-table>
      <el-table v-if="importDialog.preview?.errors?.length" :data="importDialog.preview.errors" border size="small" class="import-result">
        <el-table-column prop="row" label="行号" width="80" />
        <el-table-column prop="message" label="提示" />
      </el-table>
      <el-result
        v-if="importDialog.result"
        :icon="importResultIcon"
        :title="importResultTitle"
        :sub-title="`二维码 ${importDialog.result.scan_bindings_created || 0} 条，借用/出库 ${importDialog.result.checkout_records_created || 0} 条，维修 ${importDialog.result.repair_records_created || 0} 条，处置 ${importDialog.result.scrap_requests_created || 0} 条`"
      />
      <div v-if="importDialog.result?.errors?.length > IMPORT_ERROR_DISPLAY_LIMIT" class="import-preview-note">
        失败明细较多，当前展示前 {{ IMPORT_ERROR_DISPLAY_LIMIT }} 条。
      </div>
      <el-table v-if="importDialog.result?.errors?.length" :data="importResultErrorRows" border size="small" class="import-result" max-height="260">
        <el-table-column prop="row" label="原始行号" width="100" />
        <el-table-column prop="stage" label="阶段" width="90" />
        <el-table-column prop="message" label="失败原因" min-width="320" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ArrowDown } from '@element-plus/icons-vue'
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { assetStatuses, batchCheckinAssets, batchCheckoutAssets, batchCreateScrapRequests, batchUpdateAssets, downloadAssetImportTemplate, editableAssetStatuses, getAssets, importAssets, previewAssetsFromExcel, previewAssetsFromText, statusMap, updateAsset } from '../../api/asset'
import { getCompanies } from '../../api/company'
import { getLocations } from '../../api/location'
import { getDeviceTypes, getProducts } from '../../api/product'
import { createRepairRecords, getRepairFaultTypes } from '../../api/repair'
import { getSuppliers } from '../../api/supplier'
import { getUsers } from '../../api/user'
import { downloadAssetCsv } from '../../api/reporting'

const router = useRouter()
const route = useRoute()
const assets = ref([])
const selected = ref([])
const assetTableRef = ref(null)
const categories = ref([])
const products = ref([])
const companies = ref([])
const users = ref([])
const filteredUsers = ref([])
const suppliers = ref([])
const locations = ref([])
const faultTypes = ref([])
const filters = reactive({ keyword: '', status: '', category: '', company: '', supplier: '', risk_filter: '' })
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const batch = reactive({ visible: false, type: 'inbound', assets: [], form: defaultBatchForm() })
const batchEdit = reactive({ visible: false, form: defaultBatchEditForm(), fields: defaultBatchEditFields() })
const IMPORT_CHUNK_SIZE = 50
const IMPORT_PREVIEW_LIMIT = 100
const IMPORT_ERROR_DISPLAY_LIMIT = 200
const importDialog = reactive({
  visible: false,
  loading: false,
  importing: false,
  overwrite: false,
  content: '',
  preview: null,
  result: null,
  progress: defaultImportProgress()
})
const editDialog = reactive({ visible: false, saving: false, form: {} })
const repairDialog = reactive({ visible: false, asset: null, assets: [], form: defaultRepairForm() })
const columnDialog = reactive({ visible: false })
const workflowHint = ref('')
const assignedStatuses = ['in_use', 'borrowed']
const unassignedStatuses = ['pending_acceptance', 'in_stock', 'idle', 'ready_scrap']
const ASSET_COLUMN_ORDER_KEY = 'itam_asset_list_column_order_v6'
const ASSET_COLUMN_VISIBILITY_KEY = 'itam_asset_list_column_visibility_v1'
const assetColumnDefs = [
  { key: 'display_id', prop: 'display_id', label: '序号', width: 90 },
  { key: 'company', prop: 'company', label: '公司', width: 140, tooltip: true },
  { key: 'category', prop: 'category', label: '类型', width: 110 },
  { key: 'product', label: '产品信息' },
  { key: 'asset_no', prop: 'asset_no', label: '资产编号', width: 160 },
  { key: 'sn', prop: 'sn', label: '序列号', width: 150 },
  { key: 'purchase_supplier_name', prop: 'purchase_supplier_name', label: '供应商', width: 150, tooltip: true },
  { key: 'price', label: '价值' },
  { key: 'current_residual_value', label: '当前残值' },
  { key: 'status', label: '状态' },
  { key: 'dept', label: '部门' },
  { key: 'owner', label: '使用人' },
  { key: 'remark', prop: 'remark', label: '备注', minWidth: 160, tooltip: true },
  { key: 'purchase_date', prop: 'purchase_date', label: '采购时间', width: 120 },
  { key: 'purchase_approval_no', prop: 'purchase_approval_no', label: '采购审批单号', width: 150, tooltip: true },
  { key: 'retirement_years', label: '退役年限' },
  { key: 'retirement_date', label: '预计退役时间' }
]
const DEFAULT_ASSET_COLUMN_ORDER = [
  'display_id',
  'company',
  'category',
  'product',
  'asset_no',
  'sn',
  'purchase_supplier_name',
  'price',
  'current_residual_value',
  'status',
  'dept',
  'owner',
  'remark',
  'purchase_date',
  'purchase_approval_no',
  'retirement_years',
  'retirement_date'
]
const columnOrder = ref(loadColumnOrder())
const columnVisibility = ref(loadColumnVisibility())
const outboundTargetOptions = [
  { label: '人员', value: 'user' },
  { label: '地址', value: 'location' }
]

const batchTitle = computed(() => ({ inbound: '批量入库', outbound: '批量出库', scrap: '批量申请报废' }[batch.type]))
const realCompanies = computed(() => companies.value.filter(item => !item.virtual && item.name !== '未设置公司'))
const activeLocations = computed(() => locations.value.filter(item => item.status !== '停用'))
const activeFaultTypes = computed(() => faultTypes.value.filter(item => item.enabled !== '停用'))
const batchEditSelectedCount = computed(() => Object.values(batchEdit.fields).filter(Boolean).length)
const canConfirmImport = computed(() => importDialog.preview?.valid > 0 && !importDialog.importing)
const importPreviewRows = computed(() => (importDialog.preview?.items || []).slice(0, IMPORT_PREVIEW_LIMIT))
const importResultErrorRows = computed(() => (importDialog.result?.errors || []).slice(0, IMPORT_ERROR_DISPLAY_LIMIT))
const importProgressPercentage = computed(() => {
  if (!importDialog.progress.total) return 0
  return Math.min(100, Math.round(importDialog.progress.processed / importDialog.progress.total * 100))
})
const importProgressStatusLabel = computed(() => ({
  preparing: '准备中',
  importing: '导入中',
  retrying: '重试中',
  completed: '已完成',
  partial: '部分失败',
  failed: '失败'
})[importDialog.progress.status] || '等待')
const importProgressTagType = computed(() => ({
  completed: 'success',
  partial: 'warning',
  failed: 'danger',
  retrying: 'warning'
})[importDialog.progress.status] || 'primary')
const importProgressBarStatus = computed(() => {
  if (importDialog.progress.status === 'completed') return 'success'
  if (['partial', 'failed'].includes(importDialog.progress.status)) return 'exception'
  return undefined
})
const importProgressTitle = computed(() => {
  if (importDialog.progress.status === 'completed') return '资产导入完成'
  if (importDialog.progress.status === 'partial') return '资产导入完成，部分数据失败'
  if (importDialog.progress.status === 'failed') return '资产导入未完成'
  return '正在导入资产'
})
const importResultIcon = computed(() => {
  if (importDialog.progress.status === 'failed') return 'error'
  return importDialog.result?.errors?.length ? 'warning' : 'success'
})
const importResultTitle = computed(() => {
  if (importDialog.progress.status === 'failed') {
    return `导入已停止：已处理 ${importDialog.progress.processed}/${importDialog.progress.total} 条`
  }
  if (importDialog.result?.errors?.length) {
    return `导入完成，${importDialog.result.errors.length} 条需要处理`
  }
  return `导入完成：新增 ${importDialog.result?.created || 0} 条，更新 ${importDialog.result?.updated || 0} 条`
})
const configurableAssetColumns = computed(() => {
  const map = Object.fromEntries(assetColumnDefs.map(item => [item.key, item]))
  return columnOrder.value.map(key => map[key]).filter(Boolean)
})
const orderedAssetColumns = computed(() => configurableAssetColumns.value.filter(column => columnVisibility.value[column.key] !== false))
const visibleColumnCount = computed(() => orderedAssetColumns.value.length)

onMounted(async () => {
  applyWorkflowQuery()
  await Promise.all([loadAssets(), loadUsers(), loadTypes(), loadProducts(), loadSuppliers(), loadCompanies(), loadLocations(), loadFaultTypes()])
})

async function loadAssets() {
  const data = await getAssets({ ...filters, page: pagination.page, page_size: pagination.pageSize })
  assets.value = data.list
  pagination.total = data.total
}

function clearAssetSelection() {
  selected.value = []
  nextTick(() => assetTableRef.value?.clearSelection())
}

function refreshAssets() {
  clearAssetSelection()
  pagination.page = 1
  loadAssets()
}

function handleAssetPageSizeChange() {
  pagination.page = 1
  loadAssets()
}

function loadColumnOrder() {
  const defaults = normalizeColumnOrder(DEFAULT_ASSET_COLUMN_ORDER)
  try {
    const saved = JSON.parse(localStorage.getItem(ASSET_COLUMN_ORDER_KEY) || '[]')
    const valid = Array.isArray(saved) ? saved.filter(key => defaults.includes(key)) : []
    return [...valid, ...defaults.filter(key => !valid.includes(key))]
  } catch {
    return defaults
  }
}

function loadColumnVisibility() {
  const keys = assetColumnDefs.map(item => item.key)
  try {
    const saved = JSON.parse(localStorage.getItem(ASSET_COLUMN_VISIBILITY_KEY) || '{}')
    return Object.fromEntries(keys.map(key => [key, saved?.[key] !== false]))
  } catch {
    return Object.fromEntries(keys.map(key => [key, true]))
  }
}

function normalizeColumnOrder(order) {
  const knownKeys = assetColumnDefs.map(item => item.key)
  const valid = order.filter(key => knownKeys.includes(key))
  return [...valid, ...knownKeys.filter(key => !valid.includes(key))]
}

function saveColumnOrder() {
  localStorage.setItem(ASSET_COLUMN_ORDER_KEY, JSON.stringify(columnOrder.value))
}

function saveColumnVisibility() {
  localStorage.setItem(ASSET_COLUMN_VISIBILITY_KEY, JSON.stringify(columnVisibility.value))
}

function toggleColumn(key, visible) {
  if (!visible && visibleColumnCount.value <= 1) return
  columnVisibility.value = { ...columnVisibility.value, [key]: visible !== false }
  saveColumnVisibility()
}

function moveColumn(index, direction) {
  const nextIndex = index + direction
  if (nextIndex < 0 || nextIndex >= columnOrder.value.length) return
  const next = [...columnOrder.value]
  const [item] = next.splice(index, 1)
  next.splice(nextIndex, 0, item)
  columnOrder.value = next
  saveColumnOrder()
}

function resetColumnSettings() {
  columnOrder.value = normalizeColumnOrder(DEFAULT_ASSET_COLUMN_ORDER)
  columnVisibility.value = Object.fromEntries(assetColumnDefs.map(item => [item.key, true]))
  saveColumnOrder()
  saveColumnVisibility()
}

async function loadUsers() {
  users.value = await getUsers()
  filteredUsers.value = users.value
}

async function loadTypes() {
  const types = await getDeviceTypes()
  categories.value = types.map(item => item.name)
}

async function loadProducts() {
  products.value = await getProducts()
}

async function loadCompanies() {
  companies.value = await getCompanies()
}

async function loadSuppliers() {
  suppliers.value = await getSuppliers()
}

async function loadLocations() {
  locations.value = await getLocations()
}

async function loadFaultTypes() {
  faultTypes.value = await getRepairFaultTypes()
}

function queryValue(value) {
  return Array.isArray(value) ? value[0] : value || ''
}

function applyWorkflowQuery() {
  const action = queryValue(route.query.action)
  const userId = queryValue(route.query.user_id)
  const username = queryValue(route.query.username)
  const name = queryValue(route.query.name) || username || userId
  const status = queryValue(route.query.status)
  const keyword = queryValue(route.query.keyword)
  if (status) filters.status = status
  if (keyword) filters.keyword = keyword
  if (action === 'assign' && (userId || username)) {
    filters.keyword = ''
    filters.status = 'in_stock'
    workflowHint.value = `入职资产分配：请勾选要分配给 ${name} 的在库资产，然后点击“批量出库”，系统会默认带入该员工。`
  }
  if (action === 'reclaim' && (userId || username)) {
    filters.keyword = userId || username
    filters.status = ''
    workflowHint.value = `离职资产收回：已按 ${name} 筛选相关资产，请勾选在用、借出或已出库资产后点击“批量入库”。`
  }
}

function defaultBatchForm() {
  return {
    outboundTarget: 'user',
    toStatus: 'in_use',
    owner_user_id: '',
    owner_name: '',
    dept_id: '',
    dept_name: '',
    location: '',
    borrow_due_date: '',
    remark: ''
  }
}

function defaultBatchEditForm() {
  return {
    name: '',
    company: '',
    sn: '',
    category: '',
    status: '',
    brand: '',
    model: '',
    spec: '',
    price: null,
    purchase_date: null,
    purchase_approval_no: '',
    purchase_supplier_name: '',
    warranty_years: null,
    retirement_years: null,
    owner_user_id: '',
    owner_name: '',
    dept_id: '',
    dept_name: '',
    location: '',
    remark: ''
  }
}

function defaultBatchEditFields() {
  return {
    name: false,
    company: false,
    sn: false,
    category: false,
    status: false,
    brand: false,
    model: false,
    spec: false,
    price: false,
    purchase_date: false,
    purchase_approval_no: false,
    purchase_supplier_name: false,
    warranty_years: false,
    retirement_years: false,
    owner_user_id: false,
    dept_id: false,
    location: false,
    remark: false
  }
}

function defaultRepairForm() {
  return {
    repair_time: new Date().toISOString().slice(0, 10),
    repair_type: '普通维修',
    fault_reason: '',
    repair_cost: 0,
    vendor: '',
    operator: '资产管理员',
    remark: ''
  }
}

function displayUser(row) {
  if (row.owner_name) return row.owner_name
  const user = findUser(row.owner_user_id || row.owner)
  return user ? user.display_name : row.owner || '未分配'
}

function displayDept(row) {
  if (row.dept_name) return row.dept_name
  const user = findUser(row.owner_user_id || row.owner)
  return user?.dept_name || row.dept || '未绑定'
}

function findUser(value) {
  if (!value) return null
  const lower = String(value).toLowerCase()
  const cn = lower.includes('cn=') ? lower.split('cn=', 2)[1].split(',', 1)[0] : ''
  return users.value.find(user => [user.user_id, user.username, user.external_id, user.email].filter(Boolean).map(String).map(item => item.toLowerCase()).includes(lower) || (cn && String(user.username).toLowerCase() === cn))
}

function userLabel(user) {
  return `${user.display_name} (${user.username}) / ${user.dept_name || user.dept_id || '未分部门'}`
}

function supplierLabel(item) {
  const meta = [item.contact, item.phone].filter(Boolean).join(' / ')
  return meta ? `${item.name} (${meta})` : item.name
}

function warrantyExpirePreview(form) {
  if (!form?.purchase_date || !form?.warranty_years) return form?.warranty_expire_date || ''
  return addYears(form.purchase_date, Number(form.warranty_years))
}

function retirementDatePreview(form) {
  if (!form?.purchase_date || !form?.retirement_years) return form?.retirement_date || ''
  return addYears(form.purchase_date, Number(form.retirement_years))
}

function addYears(value, years) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime()) || !years) return ''
  date.setFullYear(date.getFullYear() + Number(years))
  return date.toISOString().slice(0, 10)
}

function searchUsers(query = '') {
  const keyword = query.trim().toLowerCase()
  filteredUsers.value = !keyword
    ? users.value
    : users.value.filter(user =>
        [user.user_id, user.username, user.display_name, user.email, user.dept_id, user.dept_name, user.external_id]
          .join(' ')
          .toLowerCase()
          .includes(keyword)
      )
}

function fillUserToForm(form, userId) {
  const user = users.value.find(item => item.user_id === userId)
  form.owner_user_id = userId || ''
  form.owner_name = user?.display_name || ''
  form.dept_id = user?.dept_id || user?.dept_name || ''
  form.dept_name = user?.dept_name || user?.dept_id || ''
}

function handleOutboundStatusChange(value) {
  if (value !== 'out_stock') batch.form.outboundTarget = 'user'
  if (value !== 'borrowed') batch.form.borrow_due_date = ''
}

function handleOutboundTargetChange(value) {
  if (value === 'location') {
    batch.form.owner_user_id = ''
    batch.form.owner_name = ''
    batch.form.dept_id = ''
    batch.form.dept_name = ''
  }
}

function canInbound(row) {
  return !['in_stock', 'pending_scrap', 'scrapped', 'disposed', 'lost'].includes(row.status)
}

function canOutbound(row) {
  return ['in_stock', 'idle'].includes(row.status)
}

function canRepair(row) {
  return !['scrapped', 'disposed', 'lost', 'pending_scrap', 'repair'].includes(row.status)
}

function canScrap(row) {
  return !['scrapped', 'disposed', 'lost', 'pending_scrap'].includes(row.status)
}

function hasAssetOwner(row) {
  return Boolean(row.owner_user_id || row.owner)
}

function validateStatusOwner(row) {
  const statusChanged = row.original_status != null && row.status !== row.original_status
  const ownerChanged = row.original_owner_user_id != null && String(row.owner_user_id || '') !== String(row.original_owner_user_id || '')
  if (!statusChanged && !ownerChanged) return true
  if (assignedStatuses.includes(row.status) && !hasAssetOwner(row)) {
    ElMessage.warning('在用、借出或已出库状态必须先选择使用人')
    return false
  }
  if (unassignedStatuses.includes(row.status) && hasAssetOwner(row)) {
    ElMessage.warning('有使用人的资产不能直接调整为待验收、在库、闲置或待报废；请先执行入库回收并清空使用人')
    return false
  }
  return true
}

function goDetail(row) {
  router.push(`/asset/detail/${row.asset_id}`)
}

function openEdit(row) {
  const ownerUserId = row.owner_user_id || row.owner || ''
  editDialog.form = {
    ...row,
    original_asset_id: row.asset_id,
    original_status: row.status,
    original_owner_user_id: ownerUserId,
    owner_user_id: ownerUserId,
    dept_id: row.dept_id || row.dept
  }
  searchUsers('')
  editDialog.visible = true
}

function applyProductToEdit(productId) {
  const product = products.value.find(item => item.id === productId)
  if (!product) return
  Object.assign(editDialog.form, {
    product_id: product.id,
    name: product.product_name || editDialog.form.name,
    category: product.device_type || editDialog.form.category,
    brand: product.brand || '',
    model: product.model || '',
    spec: product.spec || '',
    price: Number(product.unit_price || editDialog.form.price || 0),
    location: product.default_warehouse || editDialog.form.location || '',
    retirement_years: product.retirement_years ?? editDialog.form.retirement_years
  })
}

async function submitEdit() {
  if (editDialog.saving) return
  const oldAssetId = editDialog.form.original_asset_id || editDialog.form.asset_id
  const newAssetId = String(editDialog.form.asset_id || '').trim()
  if (!newAssetId) return ElMessage.warning('资产编码不能为空')
  if (newAssetId !== oldAssetId) {
    const confirmed = await ElMessageBox.confirm(`确认将资产编码从 ${oldAssetId} 修改为 ${newAssetId}？相关生命周期、附件、维修、报废、盘点和审计记录会同步更新。`, '修改资产编码', { type: 'warning' }).then(() => true).catch(() => false)
    if (!confirmed) return
  }
  if (!validateStatusOwner(editDialog.form)) return
  editDialog.saving = true
  try {
    await updateAsset(oldAssetId, { ...editDialog.form, asset_id: newAssetId })
    editDialog.visible = false
    ElMessage.success('资产信息已更新')
    await loadAssets()
  } finally {
    editDialog.saving = false
  }
}

function openBatchEdit() {
  batchEdit.form = defaultBatchEditForm()
  batchEdit.fields = defaultBatchEditFields()
  searchUsers('')
  batchEdit.visible = true
}

function resetBatchEditFields() {
  batchEdit.fields = defaultBatchEditFields()
}

async function submitBatchEdit() {
  const payload = {}
  const emptyOverwriteFields = []
  Object.keys(batchEdit.fields).forEach(key => {
    if (!batchEdit.fields[key]) return
    const value = batchEdit.form[key]
    // 数字/日期字段为空值时视为“未填写”，阻止静默清空资产数据
    if (value === null || value === undefined || value === '') {
      emptyOverwriteFields.push(key)
      return
    }
    payload[key] = value
  })
  if (batchEdit.fields.owner_user_id) {
    if (batchEdit.form.owner_user_id) {
      payload.owner_user_id = batchEdit.form.owner_user_id
    } else {
      emptyOverwriteFields.push('owner_user_id')
    }
    if (batchEdit.form.dept_id) payload.dept_id = batchEdit.form.dept_id
    if (batchEdit.form.location) payload.location = batchEdit.form.location
  }
  if (emptyOverwriteFields.length) {
    const labels = emptyOverwriteFields.map(key => batchEditFieldLabel(key)).filter(Boolean).join('、')
    ElMessage.warning(`字段【${labels}】未填写内容，为避免清空原数据已跳过。请填写后重新提交，或取消勾选该字段。`)
    return
  }
  if (!Object.keys(payload).length) {
    ElMessage.warning('请至少勾选并填写一个要更新的字段')
    return
  }
  if ((batchEdit.fields.status || payload.owner_user_id) && selected.value.some(row => !validateStatusOwner({
    ...row,
    original_status: row.status,
    original_owner_user_id: row.owner_user_id || row.owner || '',
    ...payload
  }))) return
  await batchUpdateAssets(selected.value, payload)
  batchEdit.visible = false
  clearAssetSelection()
  ElMessage.success('批量编辑完成')
  await loadAssets()
}

function batchEditFieldLabel(key) {
  return ({
    name: '资产名称', company: '所属公司', sn: '序列号', category: '设备类型', status: '状态',
    brand: '品牌', model: '型号', spec: '规格', price: '价值', purchase_date: '采购时间',
    purchase_approval_no: '审批单号', purchase_supplier_name: '供应商', warranty_years: '维保年限',
    retirement_years: '退役年限', owner_user_id: '责任人', dept_id: '部门', location: '位置', remark: '备注'
  })[key] || key
}

function openRepair(row) {
  if (!canRepair(row)) return
  repairDialog.asset = row
  repairDialog.assets = [row]
  Object.assign(repairDialog.form, defaultRepairForm())
  repairDialog.visible = true
}

function openBatchRepair() {
  if (selected.value.some(row => !canRepair(row))) {
    ElMessage.warning('已报废、待处置登记或维修中的资产不能重复创建维修单')
    return
  }
  repairDialog.asset = selected.value[0] || null
  repairDialog.assets = [...selected.value]
  Object.assign(repairDialog.form, defaultRepairForm())
  repairDialog.visible = true
}

async function submitRepair() {
  if (!repairDialog.form.repair_time) {
    ElMessage.warning('请选择维修时间')
    return
  }
  if (!repairDialog.form.fault_reason.trim()) {
    ElMessage.warning('请选择故障类型')
    return
  }
  const result = await createRepairRecords(repairDialog.assets, repairDialog.form)
  repairDialog.visible = false
  clearAssetSelection()
  if (result?.failed) {
    showBatchOperationResult(normalizeBatchResult(result, repairDialog.assets.map(asset => asset.asset_id)))
  } else {
    ElMessage.success('维修单已创建，资产状态已更新为维修中')
  }
  await loadAssets()
}

function openBatch(type) {
  const target = selected.value
  if (!validateBatchAssets(type, target)) return
  batch.type = type
  batch.assets = target
  Object.assign(batch.form, defaultBatchForm())
  if (type === 'outbound') {
    batch.form.outboundTarget = 'user'
    applyAssignUserToBatch()
  }
  if (type === 'inbound') applyReclaimRemarkToBatch()
  searchUsers('')
  batch.visible = true
}

function applyAssignUserToBatch() {
  if (queryValue(route.query.action) !== 'assign') return
  const userId = queryValue(route.query.user_id)
  const username = queryValue(route.query.username)
  if (!userId && !username) return
  const user = users.value.find(item => item.user_id === userId || item.username === username)
  batch.form.outboundTarget = 'user'
  batch.form.toStatus = 'in_use'
  batch.form.owner_user_id = user?.user_id || userId || username
  batch.form.owner_name = user?.display_name || queryValue(route.query.name) || username
  batch.form.dept_id = user?.dept_name || user?.dept_id || ''
  batch.form.dept_name = user?.dept_name || user?.dept_id || ''
  if (!batch.form.remark) batch.form.remark = '入职资产分配'
}

function applyReclaimRemarkToBatch() {
  if (queryValue(route.query.action) !== 'reclaim') return
  if (!batch.form.remark) batch.form.remark = '离职资产收回'
}

function openSingleInbound(row) {
  if (!canInbound(row)) return
  selected.value = [row]
  openBatch('inbound')
}

function openSingleOutbound(row) {
  if (!canOutbound(row)) return
  selected.value = [row]
  openBatch('outbound')
}

function openSingleScrap(row) {
  if (!canScrap(row)) return
  selected.value = [row]
  openBatch('scrap')
}

function handleMoreCommand(command, row) {
  if (command === 'repair') openRepair(row)
  if (command === 'scrap') openSingleScrap(row)
}

function validateBatchAssets(type, rows) {
  if (type === 'outbound' && rows.some(row => !canOutbound(row))) {
    ElMessage.warning('只有在库或闲置资产可以出库；在用资产不能再次出库，请先入库回收。')
    return false
  }
  if (type === 'inbound' && rows.some(row => !canInbound(row))) {
    ElMessage.warning('在库、待处置登记或已报废资产不能执行入库。')
    return false
  }
  if (type === 'scrap' && rows.some(row => !canScrap(row))) {
    ElMessage.warning('待处置登记或已报废资产不能重复发起报废。')
    return false
  }
  return true
}

function locationLabel(item) {
  return [item.name, item.type, item.owner_dept].filter(Boolean).join(' / ')
}

function defaultImportProgress() {
  return {
    status: 'idle',
    message: '',
    total: 0,
    processed: 0,
    created: 0,
    updated: 0,
    skipped: 0,
    failed: 0,
    currentBatch: 0,
    totalBatches: 0
  }
}

function emptyImportResult(previewErrors = []) {
  return {
    created: 0,
    updated: 0,
    skipped: 0,
    scan_bindings_created: 0,
    checkout_records_created: 0,
    repair_records_created: 0,
    scrap_requests_created: 0,
    errors: previewErrors.map(error => ({ ...error, stage: '预检' })),
    assets: []
  }
}

function resetImportProgress() {
  Object.assign(importDialog.progress, defaultImportProgress())
}

function fillImportExample() {
  importDialog.content = [
    '资产编码,资产名称,设备类型,品牌,型号,序列号,价格,采购日期,采购审批单号,采购供应商,维保年限,使用人,部门,位置,状态,备注,二维码内容,状态发生时间,计划归还时间',
    'ITAM-IMPORT-001,ThinkPad X1 Carbon,笔记本电脑,Lenovo,X1 Carbon Gen 12,SN-IMPORT-001,15000,2026-06-24,OA-20260624-001,联想授权供应商,3,U-ADMIN,IT,上海IT仓,in_use,关键岗位设备,https://asset.example/nb-001,2026-06-24 09:00:00,',
    'ITAM-IMPORT-002,Dell U2723QE,显示器,Dell,U2723QE,SN-IMPORT-002,3999,2026-06-24,OA-20260624-001,Dell渠道商,3,,AUDIT,上海办公区,已报废,历史报废资产,QR-DP-001；QR-DP-001-LEGACY,2026-06-24 10:00:00,'
  ].join('\n')
  clearImportPreview()
}

async function downloadTemplate() {
  await downloadAssetImportTemplate()
}

function openImportDialog() {
  importDialog.visible = true
  importDialog.loading = false
  importDialog.importing = false
  importDialog.preview = null
  importDialog.result = null
  resetImportProgress()
}

function clearImportPreview() {
  if (importDialog.importing) return
  importDialog.preview = null
  importDialog.result = null
  resetImportProgress()
}

function beforeCloseImportDialog(done) {
  if (importDialog.importing) {
    ElMessage.warning('资产正在导入，请等待当前任务完成。')
    return
  }
  done()
}

async function previewExcelImport(file) {
  importDialog.loading = true
  importDialog.result = null
  importDialog.preview = null
  resetImportProgress()
  try {
    importDialog.preview = await previewAssetsFromExcel(file, importDialog.overwrite)
    ElMessage.success(`预览完成：${importDialog.preview.valid}/${importDialog.preview.total} 行可导入`)
  } catch (error) {
    ElMessage.error({ message: importErrorMessage(error, 'Excel 文件预览失败'), duration: 6000, showClose: true })
  } finally {
    importDialog.loading = false
  }
  return false
}

async function previewTextImport() {
  if (!importDialog.content.trim()) {
    ElMessage.warning('请先粘贴导入内容')
    return
  }
  importDialog.loading = true
  importDialog.result = null
  importDialog.preview = null
  resetImportProgress()
  try {
    importDialog.preview = await previewAssetsFromText(importDialog.content, 'frontend-text-preview', importDialog.overwrite)
    ElMessage.success(`预览完成：${importDialog.preview.valid}/${importDialog.preview.total} 行可导入`)
  } catch (error) {
    ElMessage.error({ message: importErrorMessage(error, '粘贴内容预览失败'), duration: 6000, showClose: true })
  } finally {
    importDialog.loading = false
  }
}

async function confirmImport() {
  if (!canConfirmImport.value) return
  const validEntries = importDialog.preview.items.filter(item => item.valid)
  const previewErrors = importDialog.preview.errors || []
  const aggregate = emptyImportResult(previewErrors)
  const chunks = []
  for (let index = 0; index < validEntries.length; index += IMPORT_CHUNK_SIZE) {
    chunks.push(validEntries.slice(index, index + IMPORT_CHUNK_SIZE))
  }

  importDialog.importing = true
  importDialog.result = null
  Object.assign(importDialog.progress, {
    ...defaultImportProgress(),
    status: 'preparing',
    message: `准备导入 ${validEntries.length} 条有效数据`,
    total: importDialog.preview.total,
    processed: previewErrors.length,
    failed: previewErrors.length,
    totalBatches: chunks.length
  })

  try {
    for (let batchIndex = 0; batchIndex < chunks.length; batchIndex += 1) {
      const chunk = chunks[batchIndex]
      importDialog.progress.currentBatch = batchIndex + 1
      importDialog.progress.status = 'importing'
      importDialog.progress.message = `正在提交第 ${batchIndex + 1} 批，共 ${chunks.length} 批`

      let batchResult = null
      let lastError = null
      for (let attempt = 1; attempt <= 3; attempt += 1) {
        try {
          if (attempt > 1) {
            importDialog.progress.status = 'retrying'
            importDialog.progress.message = `第 ${batchIndex + 1} 批提交失败，正在第 ${attempt - 1} 次重试`
            await new Promise(resolve => window.setTimeout(resolve, 600 * attempt))
          }
          batchResult = await importAssets(
            chunk.map(item => item.data),
            `frontend-confirm-import-${batchIndex + 1}`,
            importDialog.overwrite
          )
          break
        } catch (error) {
          lastError = error
        }
      }

      if (!batchResult) {
        const message = importErrorMessage(lastError, `第 ${batchIndex + 1} 批提交失败`)
        aggregate.errors.push({
          row: `${chunk[0]?.row || '-'}-${chunk[chunk.length - 1]?.row || '-'}`,
          stage: '提交',
          message
        })
        importDialog.progress.status = 'failed'
        importDialog.progress.failed = aggregate.errors.length
        importDialog.progress.message = `第 ${batchIndex + 1} 批连续失败，导入已停止`
        break
      }

      aggregate.created += batchResult.created
      aggregate.updated += batchResult.updated
      aggregate.skipped += batchResult.skipped
      aggregate.scan_bindings_created += batchResult.scan_bindings_created
      aggregate.checkout_records_created += batchResult.checkout_records_created
      aggregate.repair_records_created += batchResult.repair_records_created
      aggregate.scrap_requests_created += batchResult.scrap_requests_created
      aggregate.errors.push(...batchResult.errors.map(error => ({
        ...error,
        row: chunk[Math.max(0, Number(error.row || 1) - 1)]?.row || error.row,
        stage: '导入'
      })))

      importDialog.progress.processed += chunk.length
      importDialog.progress.created = aggregate.created
      importDialog.progress.updated = aggregate.updated
      importDialog.progress.skipped = aggregate.skipped
      importDialog.progress.failed = aggregate.errors.length
      importDialog.progress.message = `第 ${batchIndex + 1} 批已完成`
    }

    importDialog.result = aggregate
    importDialog.preview = null
    if (importDialog.progress.status !== 'failed') {
      importDialog.progress.processed = importDialog.progress.total
      importDialog.progress.status = aggregate.errors.length ? 'partial' : 'completed'
      importDialog.progress.message = aggregate.errors.length
        ? `导入结束，${aggregate.errors.length} 条数据需要处理`
        : '所有数据已成功处理'
    }
    if (importDialog.progress.status === 'failed') {
      ElMessage.error({ message: importDialog.progress.message, duration: 6000, showClose: true })
    } else if (aggregate.errors.length) {
      ElMessage.warning(`导入结束：新增 ${aggregate.created} 条，更新 ${aggregate.updated} 条，失败 ${aggregate.errors.length} 条`)
    } else {
      ElMessage.success(`导入完成：新增 ${aggregate.created} 条，更新 ${aggregate.updated} 条；自动建借用/出库 ${aggregate.checkout_records_created} 条、维修 ${aggregate.repair_records_created} 条、处置 ${aggregate.scrap_requests_created} 条`)
    }
    await loadAssets()
  } catch (error) {
    importDialog.progress.status = 'failed'
    importDialog.progress.message = importErrorMessage(error, '导入任务异常终止')
    ElMessage.error({ message: importErrorMessage(error, '确认导入失败'), duration: 6000, showClose: true })
  } finally {
    importDialog.importing = false
  }
}

function importErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail
  if (Array.isArray(detail)) return `${fallback}：${detail.map(item => item.msg || item.message || JSON.stringify(item)).join('；')}`
  if (detail) return `${fallback}：${detail}`
  if (error?.message) return `${fallback}：${error.message}`
  return fallback
}

function showBatchOperationResult(results) {
  const success = results.filter(item => item.ok).length
  const failed = results.length - success
  const firstFailed = results.find(item => !item.ok)
  ElMessage.warning({
    message: `${batchTitle.value}完成，成功 ${success}，失败 ${failed}${firstFailed ? `；${firstFailed.asset_id}: ${firstFailed.message}` : ''}`,
    duration: 7000,
    showClose: true
  })
}

function normalizeBatchResult(result, assetIds = []) {
  const failedIds = new Set((result?.errors || []).map(item => item.asset_id))
  const rows = assetIds.filter(asset_id => !failedIds.has(asset_id)).map(asset_id => ({ asset_id, ok: true }))
  return [
    ...rows,
    ...(result?.errors || []).map(item => ({ asset_id: item.asset_id, ok: false, message: item.message || '执行失败' }))
  ]
}

async function submitBatch() {
  if (!validateBatchAssets(batch.type, batch.assets)) return
  if (batch.type === 'inbound') {
    if (!batch.form.location) {
      ElMessage.warning('请选择入库地址')
      return
    }
  }
  if (batch.type === 'outbound') {
    const isLocationOutbound = batch.form.toStatus === 'out_stock' && batch.form.outboundTarget === 'location'
    if (isLocationOutbound && !batch.form.location) {
      ElMessage.warning('请选择出库地址')
      return
    }
    if (!isLocationOutbound && !batch.form.owner_user_id) {
      ElMessage.warning(batch.form.toStatus === 'borrowed' ? '请选择借用人' : '请选择领用人')
      return
    }
    if (batch.form.toStatus === 'borrowed' && !batch.form.borrow_due_date) {
      ElMessage.warning('请选择借用到期时间')
      return
    }
    if (isLocationOutbound) {
      batch.form.owner_user_id = ''
      batch.form.owner_name = ''
      batch.form.dept_id = ''
      batch.form.dept_name = ''
    } else {
      batch.form.outboundTarget = 'user'
    }
  }
  const assetIds = batch.assets.map(asset => asset.asset_id)
  let results = []
  if (batch.type === 'inbound') {
    const result = await batchCheckinAssets(assetIds, batch.form)
    results = normalizeBatchResult(result, assetIds)
  } else if (batch.type === 'outbound') {
    const result = await batchCheckoutAssets(assetIds, batch.form)
    results = normalizeBatchResult(result, assetIds)
  } else {
    const result = await batchCreateScrapRequests(assetIds, {})
    const errorMap = new Map((result.errors || []).map(item => [item.asset_id, item.message]))
    results = assetIds.map(asset_id => ({
      asset_id,
      ok: !errorMap.has(asset_id),
      message: errorMap.get(asset_id) || ''
    }))
    if (result.retirement_flow_no) {
      ElMessage.success(`已创建报废处置登记流程 ${result.retirement_flow_no}`)
    }
  }
  if (results.some(item => !item.ok)) {
    showBatchOperationResult(results)
    batch.visible = false
    clearAssetSelection()
    await loadAssets()
    return
  }
  ElMessage.success(`${batchTitle.value}完成`)
  batch.visible = false
  clearAssetSelection()
  await loadAssets()
}

function isWorkflowLockedStatus(status) {
  return ['pending_scrap', 'scrapped', 'disposed', 'lost'].includes(status)
}

function manualStatusOptions(currentStatus) {
  const options = [...editableAssetStatuses]
  if (isWorkflowLockedStatus(currentStatus) && statusMap[currentStatus]) {
    options.push({ ...statusMap[currentStatus], disabled: true })
  }
  return options
}
</script>

<style scoped>
.selection-alert {
  margin-bottom: 12px;
}

.workflow-alert {
  margin-top: -4px;
}

.asset-name {
  display: grid;
  gap: 4px;
}

.asset-name span {
  color: var(--muted);
  font-size: 12px;
}

.edit-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.edit-grid-wide {
  grid-column: 1 / -1;
}

:deep(.asset-edit-dialog .el-dialog__body) {
  max-height: calc(100vh - 180px);
  overflow-y: auto;
}

.batch-form,
.import-textarea,
.import-result,
.repair-form {
  margin-top: 16px;
}

.batch-edit-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
  padding: 10px 12px;
  border: 1px solid #edf4ff;
  border-radius: 8px;
  background: var(--panel-soft);
  color: var(--muted);
  font-size: 13px;
}

.batch-edit-grid {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
}

.repair-asset,
.dialog-alert {
  margin-bottom: 16px;
}

.column-order-list {
  display: grid;
  gap: 8px;
  margin-top: 14px;
}

.column-order-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid #e5edf7;
  border-radius: 8px;
  background: #fff;
}

.column-order-row span {
  font-weight: 600;
  color: var(--text);
}

.column-order-row :deep(.el-checkbox) {
  min-width: 0;
  flex: 1;
  height: auto;
  margin-right: 0;
}

.column-order-row :deep(.el-checkbox__label) {
  font-weight: 600;
  color: var(--text);
  white-space: normal;
}

.upload-row,
.import-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 12px;
}

.header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.upload-row {
  justify-content: flex-start;
}

.import-progress-panel {
  display: grid;
  gap: 12px;
  margin-top: 16px;
  padding: 16px;
  border: 1px solid #d9e7f7;
  border-radius: 8px;
  background: #f7faff;
}

.import-preview-note {
  margin-top: 12px;
  color: var(--muted);
  font-size: 13px;
}

.import-progress-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.import-progress-heading > div {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.import-progress-heading strong {
  color: var(--text);
  font-size: 15px;
}

.import-progress-heading span,
.import-progress-batch {
  color: var(--muted);
  font-size: 13px;
}

.import-progress-stats {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 8px;
}

.import-progress-stats span {
  padding: 8px 10px;
  border: 1px solid #e5edf7;
  border-radius: 6px;
  background: #fff;
  color: var(--muted);
  font-size: 12px;
}

.import-progress-stats strong {
  display: block;
  margin-top: 3px;
  color: var(--text);
  font-size: 16px;
}

.import-progress-stats .import-failed-count {
  color: var(--danger);
}

.import-progress-batch {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

:deep(.toolbar .el-button) {
  flex: 0 0 auto;
}

:deep(.el-dialog__body .el-alert) {
  margin-bottom: 14px;
}

@media (max-width: 900px) {
  .edit-grid,
  .batch-edit-grid {
    grid-template-columns: 1fr;
  }

  .header-actions,
  .pagination-bar,
  .upload-row,
  .import-actions {
    justify-content: flex-start;
  }

  .import-progress-stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .header-actions .el-button,
  .toolbar .el-button {
    flex: 1 1 140px;
  }

  .pagination-bar {
    overflow-x: auto;
  }
}
</style>
