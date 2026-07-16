<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">资产管理</h2>
        <p class="page-subtitle">支持批量导入、批量编辑、批量维修、出入库、责任人绑定、供应商关联和报废审批</p>
      </div>
      <div class="header-actions">
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
      <el-table :data="assets" border stripe @selection-change="selected = $event">
        <el-table-column type="selection" width="48" />
        <el-table-column prop="display_id" label="ID" width="90" />
        <el-table-column prop="asset_id" label="资产编码" width="150" />
        <el-table-column prop="company" label="公司" width="140" show-overflow-tooltip />
        <el-table-column label="产品信息" min-width="240">
          <template #default="{ row }">
            <div class="asset-name">
              <strong>{{ row.name }}</strong>
              <span>{{ row.brand || '-' }} / {{ row.model || '-' }} / {{ row.spec || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="sn" label="序列号" width="150" />
        <el-table-column prop="category" label="类型" width="110" />
        <el-table-column prop="purchase_supplier_name" label="供应商" width="150" show-overflow-tooltip />
        <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
        <el-table-column prop="purchase_date" label="采购时间" width="120" />
        <el-table-column prop="retirement_years" label="退役年限" width="100">
          <template #default="{ row }">{{ row.retirement_years ? `${row.retirement_years} 年` : '-' }}</template>
        </el-table-column>
        <el-table-column prop="retirement_date" label="预计退役时间" width="130">
          <template #default="{ row }">{{ row.retirement_date || '-' }}</template>
        </el-table-column>
        <el-table-column label="使用人" width="150">
          <template #default="{ row }">{{ displayUser(row) }}</template>
        </el-table-column>
        <el-table-column label="部门" width="140">
          <template #default="{ row }">{{ displayDept(row) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status]?.type || 'info'">{{ statusMap[row.status]?.label || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="price" label="价值" width="120">
          <template #default="{ row }">¥{{ Number(row.price || 0).toLocaleString() }}</template>
        </el-table-column>
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

    <el-dialog v-model="editDialog.visible" title="调整资产信息" width="900px">
      <el-form :model="editDialog.form" label-width="112px">
        <AssetEditFields
          :form="editDialog.form"
          :products="products"
          :categories="categories"
          :companies="realCompanies"
          :suppliers="suppliers"
          :locations="activeLocations"
          :users="filteredUsers"
          @search-users="searchUsers"
          @select-user="userId => fillUserToForm(editDialog.form, userId)"
        />
      </el-form>
      <template #footer>
        <el-button @click="editDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitEdit">保存调整</el-button>
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
      <el-alert :title="`本次将处理 ${batch.assets.length} 个资产`" type="info" show-icon :closable="false" />
      <el-form :model="batch.form" label-width="110px" class="batch-form">
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
        <template v-if="batch.type === 'scrap'">
          <el-form-item label="申请人/部门"><el-input v-model="batch.form.applicant" /></el-form-item>
          <el-form-item label="处置方式">
            <el-select v-model="batch.form.disposal_method" style="width: 100%">
              <el-option label="环保回收" value="环保回收" />
              <el-option label="供应商回收" value="供应商回收" />
              <el-option label="内部拆件" value="内部拆件" />
              <el-option label="销毁处理" value="销毁处理" />
            </el-select>
          </el-form-item>
          <el-form-item label="预计残值"><el-input-number v-model="batch.form.estimated_residual_value" :min="0" style="width: 100%" /></el-form-item>
          <el-form-item label="报废原因"><el-input v-model="batch.form.reason" type="textarea" :rows="4" /></el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="batch.visible = false">取消</el-button>
        <el-button type="primary" @click="submitBatch">确认执行</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="repairDialog.visible" :title="repairDialog.assets.length > 1 ? '批量新增维修记录' : '新增维修记录'" width="620px">
      <el-alert v-if="repairDialog.assets.length > 1" :title="`本次将为 ${repairDialog.assets.length} 个资产创建维修记录，并更新为维修中。`" type="warning" show-icon :closable="false" class="dialog-alert" />
      <el-descriptions v-else-if="repairDialog.asset" :column="2" border class="repair-asset">
        <el-descriptions-item label="资产ID">{{ repairDialog.asset.display_id || '-' }}</el-descriptions-item>
        <el-descriptions-item label="资产编码">{{ repairDialog.asset.asset_id }}</el-descriptions-item>
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

    <el-dialog v-model="importDialog.visible" title="批量导入资产" width="1080px">
      <el-alert title="先上传文件或粘贴内容生成预览，确认数据无误后再正式导入资产。" type="info" show-icon :closable="false" />
      <div class="upload-row">
        <el-upload :show-file-list="false" accept=".xlsx,.xlsm" :before-upload="previewExcelImport">
          <el-button type="primary">上传并预览 Excel</el-button>
        </el-upload>
        <el-button @click="downloadTemplate">下载导入模板</el-button>
        <el-button @click="fillImportExample">填入粘贴示例</el-button>
      </div>
      <el-input v-model="importDialog.content" type="textarea" :rows="9" class="import-textarea" placeholder="也可以把 Excel 表格复制后粘贴到这里" @input="clearImportPreview" />
      <div class="import-actions">
        <el-button :loading="importDialog.loading" @click="previewTextImport">预览粘贴内容</el-button>
        <el-button type="primary" :disabled="!canConfirmImport" :loading="importDialog.importing" @click="confirmImport">确认导入</el-button>
      </div>
      <el-descriptions v-if="importDialog.preview" :column="3" border class="import-result">
        <el-descriptions-item label="总行数">{{ importDialog.preview.total }}</el-descriptions-item>
        <el-descriptions-item label="可导入">{{ importDialog.preview.valid }}</el-descriptions-item>
        <el-descriptions-item label="错误">{{ importDialog.preview.errors.length }}</el-descriptions-item>
      </el-descriptions>
      <el-table v-if="importDialog.preview?.items?.length" :data="importDialog.preview.items" border size="small" class="import-result" max-height="320">
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
        <el-table-column label="责任人/位置" min-width="160"><template #default="{ row }">{{ row.data.owner_user_id || row.data.location || '-' }}</template></el-table-column>
        <el-table-column label="采购价格" width="120"><template #default="{ row }">¥{{ Number(row.data.purchase_price || 0).toLocaleString() }}</template></el-table-column>
      </el-table>
      <el-table v-if="importDialog.preview?.errors?.length" :data="importDialog.preview.errors" border size="small" class="import-result">
        <el-table-column prop="row" label="行号" width="80" />
        <el-table-column prop="message" label="提示" />
      </el-table>
      <el-result v-if="importDialog.result && !importDialog.result.errors.length" icon="success" :title="`已导入 ${importDialog.result.created} 条资产`" sub-title="资产已写入后端，并生成批量导入生命周期记录" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ArrowDown } from '@element-plus/icons-vue'
import { computed, defineComponent, h, onMounted, reactive, ref, resolveComponent } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { assetStatuses, batchUpdateAssets, createScrapRequest, downloadAssetImportTemplate, editableAssetStatuses, getAssets, importAssets, inboundAsset, outboundAsset, previewAssetsFromExcel, previewAssetsFromText, statusMap, updateAsset } from '../../api/asset'
import { getCompanies } from '../../api/company'
import { getLocations } from '../../api/location'
import { getDeviceTypes, getProducts } from '../../api/product'
import { createRepairRecords, getRepairFaultTypes } from '../../api/repair'
import { getSuppliers } from '../../api/supplier'
import { getUsers } from '../../api/user'

const router = useRouter()
const route = useRoute()
const assets = ref([])
const selected = ref([])
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
const importDialog = reactive({ visible: false, loading: false, importing: false, content: '', preview: null, result: null })
const editDialog = reactive({ visible: false, form: {} })
const repairDialog = reactive({ visible: false, asset: null, assets: [], form: defaultRepairForm() })
const workflowHint = ref('')
const assignedStatuses = ['in_use', 'borrowed']
const unassignedStatuses = ['pending_purchase', 'pending_acceptance', 'in_stock', 'idle', 'ready_scrap']
const outboundTargetOptions = [
  { label: '人员', value: 'user' },
  { label: '地址', value: 'location' }
]

const batchTitle = computed(() => ({ inbound: '批量入库', outbound: '批量出库', scrap: '批量申请报废' }[batch.type]))
const realCompanies = computed(() => companies.value.filter(item => !item.virtual && item.name !== '未设置公司'))
const activeLocations = computed(() => locations.value.filter(item => item.status !== '停用'))
const activeFaultTypes = computed(() => faultTypes.value.filter(item => item.enabled !== '停用'))
const batchEditSelectedCount = computed(() => Object.values(batchEdit.fields).filter(Boolean).length)
const canConfirmImport = computed(() => importDialog.preview?.valid > 0 && !importDialog.preview.errors.length)

onMounted(async () => {
  applyWorkflowQuery()
  await Promise.all([loadAssets(), loadUsers(), loadTypes(), loadProducts(), loadSuppliers(), loadCompanies(), loadLocations(), loadFaultTypes()])
})

async function loadAssets() {
  const data = await getAssets({ ...filters, page: pagination.page, page_size: pagination.pageSize })
  assets.value = data.list
  pagination.total = data.total
  selected.value = []
}

function refreshAssets() {
  pagination.page = 1
  loadAssets()
}

function handleAssetPageSizeChange() {
  pagination.page = 1
  loadAssets()
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
    applicant: '',
    reason: '',
    disposal_method: '环保回收',
    estimated_residual_value: 0,
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
    price: 0,
    purchase_date: '',
    purchase_approval_no: '',
    purchase_supplier_name: '',
    warranty_years: 0,
    retirement_years: 0,
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
  return !['in_stock', 'pending_scrap', 'scrapped', 'disposed'].includes(row.status)
}

function canOutbound(row) {
  return ['in_stock', 'idle'].includes(row.status)
}

function canRepair(row) {
  return !['scrapped', 'disposed', 'pending_scrap', 'repair'].includes(row.status)
}

function canScrap(row) {
  return !['scrapped', 'disposed', 'pending_scrap'].includes(row.status)
}

function hasAssetOwner(row) {
  return Boolean(row.owner_user_id || row.owner)
}

function validateStatusOwner(row) {
  if (assignedStatuses.includes(row.status) && !hasAssetOwner(row)) {
    ElMessage.warning('在用、借出或已出库状态必须先选择使用人')
    return false
  }
  if (unassignedStatuses.includes(row.status) && hasAssetOwner(row)) {
    ElMessage.warning('有使用人的资产不能直接调整为待采购、待验收、在库、闲置或待报废；请先执行入库回收并清空使用人')
    return false
  }
  return true
}

function goDetail(row) {
  router.push(`/asset/detail/${row.asset_id}`)
}

function openEdit(row) {
  editDialog.form = { ...row, original_asset_id: row.asset_id, owner_user_id: row.owner_user_id || row.owner, dept_id: row.dept_id || row.dept }
  searchUsers('')
  editDialog.visible = true
}

async function submitEdit() {
  const oldAssetId = editDialog.form.original_asset_id || editDialog.form.asset_id
  const newAssetId = String(editDialog.form.asset_id || '').trim()
  if (!newAssetId) return ElMessage.warning('资产编码不能为空')
  if (newAssetId !== oldAssetId) {
    const confirmed = await ElMessageBox.confirm(`确认将资产编码从 ${oldAssetId} 修改为 ${newAssetId}？相关生命周期、附件、维修、报废、盘点和审计记录会同步更新。`, '修改资产编码', { type: 'warning' }).then(() => true).catch(() => false)
    if (!confirmed) return
  }
  if (!validateStatusOwner(editDialog.form)) return
  await updateAsset(oldAssetId, { ...editDialog.form, asset_id: newAssetId })
  editDialog.visible = false
  ElMessage.success('资产信息已更新')
  await loadAssets()
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
  Object.keys(batchEdit.fields).forEach(key => {
    if (batchEdit.fields[key]) payload[key] = batchEdit.form[key]
  })
  if (batchEdit.fields.owner_user_id) {
    payload.dept_id = batchEdit.form.dept_id
    payload.location = batchEdit.form.location
  }
  if (!Object.keys(payload).length) {
    ElMessage.warning('请至少勾选一个要更新的字段')
    return
  }
  if ((batchEdit.fields.status || batchEdit.fields.owner_user_id) && selected.value.some(row => !validateStatusOwner({ ...row, ...payload }))) return
  await batchUpdateAssets(selected.value, payload)
  batchEdit.visible = false
  selected.value = []
  ElMessage.success('批量编辑完成')
  await loadAssets()
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
    ElMessage.warning('已报废、已提交报废审批或维修中的资产不能重复创建维修单')
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
  await createRepairRecords(repairDialog.assets, repairDialog.form)
  repairDialog.visible = false
  selected.value = []
  ElMessage.success('维修单已创建，资产状态已更新为维修中')
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
    ElMessage.warning('在库、已提交报废审批或已报废资产不能执行入库。')
    return false
  }
  if (type === 'scrap' && rows.some(row => !canScrap(row))) {
    ElMessage.warning('已提交报废审批或已报废资产不能重复发起报废。')
    return false
  }
  return true
}

function locationLabel(item) {
  return [item.name, item.type, item.owner_dept].filter(Boolean).join(' / ')
}

function fillImportExample() {
  importDialog.content = [
    '资产编码,资产名称,设备类型,品牌,型号,序列号,价格,采购日期,采购审批单号,采购供应商,维保年限,使用人,部门,位置,状态,备注',
    'ITAM-IMPORT-001,ThinkPad X1 Carbon,笔记本电脑,Lenovo,X1 Carbon Gen 12,SN-IMPORT-001,15000,2026-06-24,OA-20260624-001,联想授权供应商,3,U-ADMIN,IT,上海IT仓,in_stock,关键岗位备用机',
    'ITAM-IMPORT-002,Dell U2723QE,显示器,Dell,U2723QE,SN-IMPORT-002,3999,2026-06-24,OA-20260624-001,Dell渠道商,3,U-AUDITOR,AUDIT,上海办公区,in_stock,设计部高色准显示器'
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
}

function clearImportPreview() {
  importDialog.preview = null
  importDialog.result = null
}

async function previewExcelImport(file) {
  importDialog.loading = true
  importDialog.result = null
  importDialog.preview = null
  try {
    importDialog.preview = await previewAssetsFromExcel(file)
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
  try {
    importDialog.preview = await previewAssetsFromText(importDialog.content, 'frontend-text-preview')
    ElMessage.success(`预览完成：${importDialog.preview.valid}/${importDialog.preview.total} 行可导入`)
  } catch (error) {
    ElMessage.error({ message: importErrorMessage(error, '粘贴内容预览失败'), duration: 6000, showClose: true })
  } finally {
    importDialog.loading = false
  }
}

async function confirmImport() {
  if (!canConfirmImport.value) return
  importDialog.importing = true
  try {
    const items = importDialog.preview.items.filter(item => item.valid).map(item => item.data)
    importDialog.result = await importAssets(items, 'frontend-confirm-import')
    ElMessage.success(`导入完成：新增 ${importDialog.result.created} 条，跳过 ${importDialog.result.skipped} 条`)
    importDialog.preview = null
    await loadAssets()
  } catch (error) {
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
  const results = []
  for (const asset of batch.assets) {
    try {
      if (batch.type === 'inbound') await inboundAsset(asset.asset_id, batch.form)
      if (batch.type === 'outbound') await outboundAsset(asset.asset_id, batch.form)
      if (batch.type === 'scrap') await createScrapRequest(asset.asset_id, batch.form)
      results.push({ asset_id: asset.asset_id, ok: true })
    } catch (error) {
      results.push({ asset_id: asset.asset_id, ok: false, message: error.userMessage || error?.response?.data?.detail || error.message })
    }
  }
  if (results.some(item => !item.ok)) {
    showBatchOperationResult(results)
    batch.visible = false
    selected.value = []
    await loadAssets()
    return
  }
  ElMessage.success(`${batchTitle.value}完成`)
  batch.visible = false
  selected.value = []
  await loadAssets()
}

function isWorkflowLockedStatus(status) {
  return ['pending_scrap', 'scrapped', 'disposed'].includes(status)
}

function manualStatusOptions(currentStatus) {
  const options = [...editableAssetStatuses]
  if (isWorkflowLockedStatus(currentStatus) && statusMap[currentStatus]) {
    options.push({ ...statusMap[currentStatus], disabled: true })
  }
  return options
}

const AssetEditFields = defineComponent({
  props: {
    form: { type: Object, required: true },
    products: { type: Array, required: true },
    categories: { type: Array, required: true },
    companies: { type: Array, required: true },
    suppliers: { type: Array, required: true },
    locations: { type: Array, required: true },
    users: { type: Array, required: true }
  },
  emits: ['search-users', 'select-user'],
  setup(props, { emit }) {
    function applyProduct(productId) {
      const product = props.products.find(item => item.id === productId)
      if (!product) return
      props.form.product_id = product.id
      props.form.name = product.product_name || props.form.name
      props.form.category = product.device_type || props.form.category
      props.form.brand = product.brand || ''
      props.form.model = product.model || ''
      props.form.spec = product.spec || ''
      props.form.price = Number(product.unit_price || props.form.price || 0)
      props.form.location = product.default_warehouse || props.form.location || ''
      props.form.retirement_years = product.retirement_years ?? props.form.retirement_years
    }

    return () =>
      h('div', { class: 'edit-grid' }, [
        field('产品档案', h(resolveSelect(), { modelValue: props.form.product_id, 'onUpdate:modelValue': applyProduct, filterable: true, clearable: true, placeholder: '选择产品后自动带出规格', style: 'width:100%' }, () => props.products.map(item => h(resolveOption(), { key: item.id, label: `${item.product_name} / ${item.model || '-'} / ${item.spec || '-'}`, value: item.id })))),
        field('资产编码', h(resolveInput(), { modelValue: props.form.asset_id, 'onUpdate:modelValue': value => { props.form.asset_id = value; props.form.asset_no = props.form.asset_no || value }, placeholder: '业务编码，例如 ITAM-000001' })),
        field('资产名称', h(resolveInput(), { modelValue: props.form.name, 'onUpdate:modelValue': value => (props.form.name = value) })),
        field('所属公司', h(resolveSelect(), { modelValue: props.form.company, 'onUpdate:modelValue': value => (props.form.company = value), filterable: true, clearable: true, style: 'width:100%' }, () => props.companies.map(item => h(resolveOption(), { key: item.id || item.name, label: item.name, value: item.name })))),
        field('序列号', h(resolveInput(), { modelValue: props.form.sn, 'onUpdate:modelValue': value => (props.form.sn = value) })),
        field('设备类型', h(resolveSelect(), { modelValue: props.form.category, 'onUpdate:modelValue': value => (props.form.category = value), filterable: true, allowCreate: true, defaultFirstOption: true, style: 'width:100%' }, () => props.categories.map(item => h(resolveOption(), { key: item, label: item, value: item })))),
        field('状态', h(resolveSelect(), { modelValue: props.form.status, 'onUpdate:modelValue': value => (props.form.status = value), disabled: isWorkflowLockedStatus(props.form.status), style: 'width:100%' }, () => manualStatusOptions(props.form.status).map(item => h(resolveOption(), { key: item.value, label: item.label, value: item.value, disabled: item.disabled })))),
        field('品牌', h(resolveInput(), { modelValue: props.form.brand, 'onUpdate:modelValue': value => (props.form.brand = value) })),
        field('型号', h(resolveInput(), { modelValue: props.form.model, 'onUpdate:modelValue': value => (props.form.model = value) })),
        field('规格', h(resolveInput(), { modelValue: props.form.spec, 'onUpdate:modelValue': value => (props.form.spec = value) })),
        field('价值', h(resolveInputNumber(), { modelValue: props.form.price, 'onUpdate:modelValue': value => (props.form.price = value), min: 0, style: 'width:100%' })),
        field('采购时间', h(resolveDatePicker(), { modelValue: props.form.purchase_date, 'onUpdate:modelValue': value => (props.form.purchase_date = value), type: 'date', valueFormat: 'YYYY-MM-DD', style: 'width:100%' })),
        field('采购审批单号', h(resolveInput(), { modelValue: props.form.purchase_approval_no, 'onUpdate:modelValue': value => (props.form.purchase_approval_no = value) })),
        field('采购供应商', h(resolveSelect(), { modelValue: props.form.purchase_supplier_name, 'onUpdate:modelValue': value => (props.form.purchase_supplier_name = value), filterable: true, clearable: true, allowCreate: true, defaultFirstOption: true, style: 'width:100%' }, () => props.suppliers.map(item => h(resolveOption(), { key: item.id || item.name, label: item.name, value: item.name })))),
        field('维保年限', h(resolveInputNumber(), { modelValue: props.form.warranty_years, 'onUpdate:modelValue': value => (props.form.warranty_years = value), min: 0, step: 1, precision: 0, style: 'width:100%' })),
        field('维保到期', h(resolveInput(), { modelValue: warrantyExpirePreview(props.form), disabled: true, placeholder: '根据采购时间和维保年限自动计算' })),
        field('退役年限', h(resolveInputNumber(), { modelValue: props.form.retirement_years, 'onUpdate:modelValue': value => (props.form.retirement_years = value), min: 0, step: 1, precision: 0, style: 'width:100%' })),
        field('预计退役时间', h(resolveInput(), { modelValue: retirementDatePreview(props.form), disabled: true, placeholder: '根据采购时间和退役年限自动计算' })),
        field('责任人', h(resolveSelect(), { modelValue: props.form.owner_user_id, 'onUpdate:modelValue': value => (props.form.owner_user_id = value), filterable: true, remote: true, clearable: true, reserveKeyword: true, remoteMethod: value => emit('search-users', value), style: 'width:100%', onChange: value => emit('select-user', value) }, () => props.users.map(user => h(resolveOption(), { key: user.user_id, label: `${user.display_name} (${user.username}) / ${user.dept_name || user.dept_id || '未分部门'}`, value: user.user_id })))),
        field('部门', h(resolveInput(), { modelValue: props.form.dept_id, 'onUpdate:modelValue': value => (props.form.dept_id = value), disabled: true })),
        field('位置', h(resolveSelect(), { modelValue: props.form.location, 'onUpdate:modelValue': value => (props.form.location = value), filterable: true, clearable: true, style: 'width:100%' }, () => props.locations.map(item => h(resolveOption(), { key: item.id || item.name, label: locationLabel(item), value: item.name })))),
        field('备注', h(resolveInput(), { modelValue: props.form.remark, 'onUpdate:modelValue': value => (props.form.remark = value), type: 'textarea', rows: 3, placeholder: '特殊说明，例如备用机、涉密、借测、待补配件' }))
      ])
  }
})

function field(label, child) {
  return h(resolveFormItem(), { label }, () => child)
}

function resolveFormItem() { return resolveComponent('ElFormItem') }
function resolveInput() { return resolveComponent('ElInput') }
function resolveInputNumber() { return resolveComponent('ElInputNumber') }
function resolveSelect() { return resolveComponent('ElSelect') }
function resolveOption() { return resolveComponent('ElOption') }
function resolveDatePicker() { return resolveComponent('ElDatePicker') }
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

  .header-actions .el-button,
  .toolbar .el-button {
    flex: 1 1 140px;
  }

  .pagination-bar {
    overflow-x: auto;
  }
}
</style>
